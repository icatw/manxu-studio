from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import api_logger
from app.core.security import decrypt_secret
from app.db.models import CharacterRecord, GenerationTaskRecord, ProjectRecord
from app.providers import generate_image, generate_structured_text
from app.tasks.prompts import CHARACTER_DRAFT
from app.tasks.provider_jobs import bind_image_job
from app.tasks.registry import register
from app.tasks.schemas import CharacterGenerationOutput
from app.tasks.support import report_progress, require_text_model
from app.tasks.types import TaskType


@register(TaskType.CHARACTER_DRAFT)
async def handle_character_draft(
    session: AsyncSession, task: GenerationTaskRecord
) -> dict[str, Any]:
    return await generate_characters(session, task)


async def generate_characters(session: AsyncSession, task: GenerationTaskRecord) -> dict[str, Any]:
    existing = list(
        (
            await session.scalars(
                select(CharacterRecord).where(CharacterRecord.project_id == task.project_id)
            )
        ).all()
    )
    project = await session.get(ProjectRecord, task.project_id)
    if project is None:
        raise ValueError("项目不存在")
    config = await require_text_model(session, project.owner_id)
    text_api_key = decrypt_secret(config.text_api_key_encrypted)
    image_api_key = (
        decrypt_secret(config.image_api_key_encrypted) if config.image_api_key_encrypted else None
    )
    image_model = config.image_model
    image_base_url = config.image_base_url
    title, synopsis, genre, art_style = (
        project.title,
        project.synopsis,
        project.genre,
        project.art_style,
    )
    text_base_url = config.text_base_url
    text_model = config.text_model
    await session.commit()
    await report_progress(session, task, 15)
    output = await generate_structured_text(
        base_url=text_base_url,
        model=text_model,
        api_key=text_api_key,
        system_prompt=CHARACTER_DRAFT.system,
        user_prompt=(
            f"故事标题：{title}\n故事梗概：{synopsis}\n题材：{genre}\n画风：{art_style}\n"
            '返回对象格式：{"character": {"name": string, "role": string, '
            '"appearance": string, "hairstyle": string, "outfit": string, '
            '"signature_traits": [string], "personality": string, '
            '"reference_image_prompt": string}}。参考图提示词描述单人全身立绘、'
            "纯净背景、清晰服装和辨识特征，不要出现文字或水印。"
        ),
        response_model=CharacterGenerationOutput,
    )
    generated = output.character
    await report_progress(session, task, 35)
    profile = {
        "generation_source": "ai",
        "role": generated.role,
        "appearance": generated.appearance,
        "hairstyle": generated.hairstyle,
        "outfit": generated.outfit,
        "signature_traits": generated.signature_traits,
        "personality": generated.personality,
        "visual_traits": [generated.hairstyle, *generated.signature_traits],
        "image_prompt": generated.reference_image_prompt,
    }
    character = existing[0] if existing else CharacterRecord(project_id=project.id, status="draft")
    if not existing:
        session.add(character)
    character.name = generated.name
    character.profile = cast(dict[str, object], profile)
    character.status = "draft"
    character.version = character.version + 1 if existing else 1
    character.reference_asset_id = None
    await session.flush()
    await session.commit()

    warning: str | None = None
    await report_progress(session, task, 45)
    if image_api_key:
        asset_id, resume_task_id, on_submitted = await bind_image_job(
            session, task, f"character:{character.id}"
        )
        try:
            await report_progress(session, task, 55)
            await generate_image(
                api_key=image_api_key,
                model=image_model,
                prompt=(
                    f"{art_style}，{generated.reference_image_prompt}。角色：{generated.name}。"
                    "单人全身角色设定图，纯净浅色背景，完整展示发型、服装和标志性特征，"
                    "不得出现文字、标题、边框或水印。"
                ),
                asset_id=asset_id,
                base_url=image_base_url,
                resume_task_id=resume_task_id,
                on_submitted=on_submitted,
            )
            character.reference_asset_id = asset_id
            await session.commit()
            await report_progress(session, task, 95)
        except Exception as error:
            warning = "角色文字设定已生成，但参考图生成失败；可在设置中检查图像模型后重试。"
            api_logger.warning(
                "character_reference_generation_failed",
                extra={
                    "event": "character_reference_generation_failed",
                    "task_id": str(task.id),
                    "error_type": type(error).__name__,
                },
            )
    else:
        warning = "角色文字设定已生成；账户尚未配置图像模型密钥，因此没有生成参考图。"
    result: dict[str, Any] = {
        "character_ids": [str(character.id)],
        "generation_source": "ai",
        "reference_image_generated": bool(character.reference_asset_id),
        "prompt_template": {"name": CHARACTER_DRAFT.name, "version": CHARACTER_DRAFT.version},
    }
    if warning:
        result["warnings"] = [warning]
    return result
