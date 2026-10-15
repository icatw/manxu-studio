from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import api_logger
from app.core.security import decrypt_secret
from app.db.models import CharacterRecord, GenerationTaskRecord, ProjectRecord
from app.providers import generate_image, generate_structured_text
from app.providers.errors import ProviderControlError
from app.tasks.prompts import CHARACTER_DRAFT
from app.tasks.provider_jobs import (
    bind_image_job,
    clear_image_job,
    persist_text_checkpoint,
    text_checkpoint,
)
from app.tasks.registry import register
from app.tasks.schemas import CharacterGenerationOutput, GeneratedCharacter
from app.tasks.support import report_progress, require_text_model
from app.tasks.types import TaskType


def _profile_from_generated(generated: GeneratedCharacter) -> dict[str, object]:
    return {
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

    checkpoint = text_checkpoint(task, "characters")
    locked_preserved_flags: list[bool] = []
    if checkpoint is not None:
        checkpoint_ids = [UUID(str(item)) for item in checkpoint.get("character_ids", [])]
        by_id = {character.id: character for character in existing}
        generated_characters = [
            by_id[character_id] for character_id in checkpoint_ids if character_id in by_id
        ]
        if not generated_characters:
            raise ValueError("角色文字设定检查点存在，但角色记录已丢失")
        raw_flags = checkpoint.get("reference_locked_preserved")
        if isinstance(raw_flags, list):
            locked_preserved_flags = [bool(item) for item in raw_flags]
        await report_progress(session, task, 45)
    else:
        await report_progress(session, task, 15)
        output = await generate_structured_text(
            base_url=text_base_url,
            model=text_model,
            api_key=text_api_key,
            system_prompt=CHARACTER_DRAFT.system,
            user_prompt=(
                f"故事标题：{title}\n故事梗概：{synopsis}\n题材：{genre}\n画风：{art_style}\n"
                "根据剧情设计完整可复用角色阵容（主角、重要配角、必要时反派），"
                "通常 2 到 6 人，避免只返回单一主角。\n"
                '返回对象格式：{"characters":[{"name":string,"role":string,'
                '"appearance":string,"hairstyle":string,"outfit":string,'
                '"signature_traits":[string],"personality":string,'
                '"reference_image_prompt":string}]}。参考图提示词描述单人全身立绘、'
                "纯净背景、清晰服装和辨识特征，不要出现文字或水印。"
            ),
            response_model=CharacterGenerationOutput,
        )
        await report_progress(session, task, 35)
        generated_characters = []
        for index, generated in enumerate(output.characters):
            character = (
                existing[index]
                if index < len(existing)
                else CharacterRecord(project_id=project.id, status="draft")
            )
            if index >= len(existing):
                session.add(character)
            keep_reference = (
                index < len(existing)
                and bool(character.reference_locked)
                and character.reference_asset_id is not None
            )
            character.name = generated.name
            character.profile = _profile_from_generated(generated)
            character.status = "draft"
            character.version = character.version + 1 if index < len(existing) else 1
            if not keep_reference:
                character.reference_asset_id = None
            await session.flush()
            if not keep_reference:
                # New text must not resume an image job submitted for a previous profile.
                await clear_image_job(session, task, f"character:{character.id}")
            locked_preserved_flags.append(keep_reference)
            generated_characters.append(character)
        await persist_text_checkpoint(
            session,
            task,
            "characters",
            {
                "character_ids": [str(character.id) for character in generated_characters],
                "reference_locked_preserved": locked_preserved_flags,
            },
        )
        await report_progress(session, task, 45)

    character_ids = [str(character.id) for character in generated_characters]
    warnings: list[str] = []
    if not image_api_key:
        warnings.append("角色文字设定已生成；账户尚未配置图像模型密钥，因此没有生成参考图。")
        await report_progress(session, task, 95)
        return {
            "character_ids": character_ids,
            "generation_source": "ai",
            "reference_images_generated": 0,
            "reference_image_generated": False,
            "reference_locked_preserved": any(locked_preserved_flags),
            "warnings": warnings,
            "prompt_template": {"name": CHARACTER_DRAFT.name, "version": CHARACTER_DRAFT.version},
        }

    images_generated = 0
    total = max(len(generated_characters), 1)
    for index, character in enumerate(generated_characters):
        keep_reference = bool(
            character.reference_locked and character.reference_asset_id is not None
        )
        if index < len(locked_preserved_flags):
            keep_reference = locked_preserved_flags[index] or keep_reference
        if keep_reference:
            images_generated += 1
            warnings.append(f"{character.name}文字设定已更新；定妆照已锁定，未替换参考图。")
            await report_progress(session, task, 45 + round(50 * (index + 1) / total))
            continue

        image_prompt = str(character.profile.get("image_prompt", "")).strip()
        image_job = await bind_image_job(session, task, f"character:{character.id}")
        try:
            await generate_image(
                api_key=image_api_key,
                model=image_model,
                prompt=(
                    f"{art_style}，{image_prompt}。角色：{character.name}。"
                    "单人全身角色设定图，纯净浅色背景，完整展示发型、服装和标志性特征，"
                    "不得出现文字、标题、边框或水印。"
                ),
                asset_id=image_job.asset_id,
                base_url=image_base_url,
                resume_task_id=image_job.resume_task_id,
                on_submit_started=image_job.on_submit_started,
                on_submit_rejected=image_job.on_submit_rejected,
                on_submitted=image_job.on_submitted,
            )
        except ProviderControlError:
            raise
        except ValueError:
            warnings.append(
                f"{character.name}文字设定已生成，但参考图生成失败；可在设置中检查图像模型后重试。"
            )
            api_logger.warning(
                "character_reference_generation_failed",
                extra={
                    "event": "character_reference_generation_failed",
                    "task_id": str(task.id),
                    "character_id": str(character.id),
                    "error_type": "ValueError",
                },
            )
        else:
            character.reference_asset_id = image_job.asset_id
            await session.commit()
            images_generated += 1
        await report_progress(session, task, 45 + round(50 * (index + 1) / total))

    return {
        "character_ids": character_ids,
        "generation_source": "ai",
        "reference_images_generated": images_generated,
        "reference_image_generated": images_generated > 0,
        "reference_locked_preserved": any(locked_preserved_flags),
        "warnings": warnings,
        "prompt_template": {"name": CHARACTER_DRAFT.name, "version": CHARACTER_DRAFT.version},
    }
