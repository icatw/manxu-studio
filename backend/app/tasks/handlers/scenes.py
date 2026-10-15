from typing import Any, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import api_logger
from app.core.security import decrypt_secret
from app.db.models import (
    AccountModelConfigRecord,
    EpisodeRecord,
    GenerationTaskRecord,
    ProjectRecord,
    SceneRecord,
)
from app.providers import generate_image, generate_structured_text
from app.providers.errors import ProviderControlError
from app.tasks.prompts import SCENE_DRAFT
from app.tasks.provider_jobs import (
    bind_image_job,
    clear_image_job,
    persist_text_checkpoint,
    text_checkpoint,
)
from app.tasks.registry import register
from app.tasks.schemas import SceneGenerationOutput
from app.tasks.support import report_progress, require_text_model
from app.tasks.types import TaskType


@register(TaskType.SCENE_DRAFT)
async def handle_scene_draft(session: AsyncSession, task: GenerationTaskRecord) -> dict[str, Any]:
    return await generate_scenes(session, task, image_only=False)


@register(TaskType.SCENE_REFERENCE_IMAGES)
async def handle_scene_reference_images(
    session: AsyncSession, task: GenerationTaskRecord
) -> dict[str, Any]:
    return await generate_scenes(session, task, image_only=True)


async def generate_scenes(
    session: AsyncSession,
    task: GenerationTaskRecord,
    *,
    image_only: bool = False,
) -> dict[str, Any]:
    existing = list(
        (
            await session.scalars(
                select(SceneRecord).where(SceneRecord.project_id == task.project_id)
            )
        ).all()
    )
    project = await session.get(ProjectRecord, task.project_id)
    if project is None:
        raise ValueError("项目不存在")
    episode_id = task.request_data.get("episode_id")
    episode = await session.get(EpisodeRecord, UUID(str(episode_id))) if episode_id else None
    config = (
        await session.get(AccountModelConfigRecord, project.owner_id)
        if image_only
        else await require_text_model(session, project.owner_id)
    )
    if config is None:
        raise ValueError("请先在设置中配置模型")
    if image_only:
        if not existing:
            raise ValueError("当前项目没有可生成参考图的场景")
        generated_scenes = existing
    else:
        checkpoint = text_checkpoint(task, "scenes")
        if checkpoint is not None:
            checkpoint_ids = [UUID(str(item)) for item in checkpoint.get("scene_ids", [])]
            by_id = {scene.id: scene for scene in existing}
            generated_scenes = [by_id[scene_id] for scene_id in checkpoint_ids if scene_id in by_id]
            if not generated_scenes:
                raise ValueError("场景文字设定检查点存在，但场景记录已丢失")
            await report_progress(session, task, 45)
        else:
            text_api_key = decrypt_secret(config.text_api_key_encrypted)
            title, synopsis, genre, art_style = (
                project.title,
                episode.synopsis if episode else project.synopsis,
                project.genre,
                project.art_style,
            )
            guidance = str(task.request_data.get("guidance", ""))
            await session.commit()
            await report_progress(session, task, 15)
            output = await generate_structured_text(
                base_url=config.text_base_url,
                model=config.text_model,
                api_key=text_api_key,
                system_prompt=SCENE_DRAFT.system,
                user_prompt=(
                    f"作品：{title}\n梗概：{synopsis}\n题材：{genre}\n画风：{art_style}\n"
                    f'补充要求：{guidance or "无"}\n返回格式：{{"scenes":[{{"name":string,'
                    '"description":string,"lighting":string,"palette":string,'
                    '"visual_traits":[string]}}]}。'
                ),
                response_model=SceneGenerationOutput,
            )
            await report_progress(session, task, 45)
            generated_scenes = []
            for index, generated in enumerate(output.scenes):
                scene = (
                    existing[index] if index < len(existing) else SceneRecord(project_id=project.id)
                )
                if index >= len(existing):
                    session.add(scene)
                scene.name = generated.name
                scene.profile = cast(dict[str, object], generated.model_dump(exclude={"name"}))
                scene.status = "draft"
                scene.version = scene.version + 1 if index < len(existing) else 1
                scene.reference_asset_id = None
                await session.flush()
                await clear_image_job(session, task, f"scene:{scene.id}")
                generated_scenes.append(scene)
            await persist_text_checkpoint(
                session,
                task,
                "scenes",
                {"scene_ids": [str(scene.id) for scene in generated_scenes]},
            )

    scene_ids = [str(scene.id) for scene in generated_scenes]
    warnings: list[str] = []
    image_api_key_encrypted = getattr(config, "image_api_key_encrypted", None)
    if not image_api_key_encrypted:
        warnings.append("场景文字设定已保存；账户尚未配置图像模型 API Key，因此没有生成参考图。")
    else:
        image_api_key = decrypt_secret(image_api_key_encrypted)
        image_model = getattr(config, "image_model", None) or "qwen-image-3.0-pro"
        image_base_url = getattr(config, "image_base_url", None)
        scenes_to_render = [scene for scene in generated_scenes if not scene.reference_asset_id]
        if not image_only:
            await report_progress(session, task, 55)
        for index, scene in enumerate(scenes_to_render):
            image_job = await bind_image_job(session, task, f"scene:{scene.id}")
            profile = scene.profile
            visual_traits = profile.get("visual_traits", [])
            visual_traits = visual_traits if isinstance(visual_traits, list) else []
            prompt = "\n".join(
                item
                for item in [
                    project.art_style,
                    f"场景：{scene.name}",
                    str(profile.get("description", "")),
                    f"光线：{profile.get('lighting', '')}",
                    f"色彩：{profile.get('palette', '')}",
                    "视觉特征：" + "、".join(str(item) for item in visual_traits),
                    "漫剧场景环境概念图，宽幅构图，画面中不出现人物、文字、标注或水印。",
                ]
                if item
            )
            # Persist scene state before crossing the provider boundary. A failed
            # database commit must fail the task, not become a partial image warning.
            await session.commit()
            try:
                await generate_image(
                    api_key=image_api_key,
                    model=image_model,
                    prompt=prompt,
                    asset_id=image_job.asset_id,
                    base_url=image_base_url,
                    resume_task_id=image_job.resume_task_id,
                    on_submit_started=image_job.on_submit_started,
                    on_submit_rejected=image_job.on_submit_rejected,
                    on_submitted=image_job.on_submitted,
                )
            except ProviderControlError:
                raise
            except ValueError as error:
                warnings.append(f"{scene.name}参考图生成失败，可稍后单独重试。")
                api_logger.warning(
                    "scene_reference_generation_failed",
                    extra={
                        "event": "scene_reference_generation_failed",
                        "task_id": str(task.id),
                        "scene_id": str(scene.id),
                        "error_type": type(error).__name__,
                    },
                )
            else:
                scene.reference_asset_id = image_job.asset_id
                await session.commit()
            await report_progress(
                session,
                task,
                55 + round(40 * (index + 1) / max(len(scenes_to_render), 1)),
            )
    return {
        "scene_ids": scene_ids,
        "reference_images_generated": sum(
            bool(scene.reference_asset_id) for scene in generated_scenes
        ),
        "warnings": warnings,
        "prompt_template": {"name": SCENE_DRAFT.name, "version": SCENE_DRAFT.version},
    }
