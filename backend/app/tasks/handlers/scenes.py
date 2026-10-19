import unicodedata
from typing import Any, Literal, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import api_logger
from app.core.security import decrypt_secret
from app.db.models import (
    EpisodeRecord,
    GenerationTaskRecord,
    PanelRecord,
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
from app.tasks.support import report_progress, require_image_model, require_text_model
from app.tasks.types import TaskType

CastMode = Literal["append", "replace"]


def _normalize_cast_name(name: str) -> str:
    compact = "".join(unicodedata.normalize("NFKC", name).split())
    return compact.casefold()


def _request_data(task: GenerationTaskRecord) -> dict[str, Any]:
    raw = getattr(task, "request_data", None)
    return raw if isinstance(raw, dict) else {}


def _cast_mode(task: GenerationTaskRecord) -> CastMode:
    data = _request_data(task)
    raw = data.get("cast_mode")
    if raw not in ("append", "replace"):
        raw = data.get("scene_cast_mode")
    if raw == "replace":
        return "replace"
    return "append"


def _request_uuids(task: GenerationTaskRecord, key: str) -> list[UUID]:
    raw = _request_data(task).get(key)
    if not isinstance(raw, list):
        return []
    ids: list[UUID] = []
    for item in raw:
        try:
            ids.append(UUID(str(item)))
        except ValueError:
            continue
    return ids


async def _clear_scene_id_from_panels(
    session: AsyncSession, project_id: UUID, removed_ids: set[UUID]
) -> None:
    if not removed_ids:
        return
    episode_ids = list(
        (
            await session.scalars(
                select(EpisodeRecord.id).where(EpisodeRecord.project_id == project_id)
            )
        ).all()
    )
    if not episode_ids:
        return
    panels = list(
        (
            await session.scalars(
                select(PanelRecord).where(PanelRecord.episode_id.in_(episode_ids))
            )
        ).all()
    )
    for panel in panels:
        if panel.scene_id in removed_ids:
            panel.scene_id = None


@register(TaskType.SCENE_DRAFT)
async def handle_scene_draft(session: AsyncSession, task: GenerationTaskRecord) -> dict[str, Any]:
    text_only = bool(_request_data(task).get("text_only"))
    return await generate_scenes(session, task, image_only=False, text_only=text_only)


@register(TaskType.SCENE_REFERENCE_IMAGES)
async def handle_scene_reference_images(
    session: AsyncSession, task: GenerationTaskRecord
) -> dict[str, Any]:
    return await generate_scenes(session, task, image_only=True, text_only=False)


async def generate_scenes(
    session: AsyncSession,
    task: GenerationTaskRecord,
    *,
    image_only: bool = False,
    text_only: bool = False,
) -> dict[str, Any]:
    if image_only and text_only:
        raise ValueError("image_only 与 text_only 不能同时为 true")
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
    request_data = _request_data(task)
    episode_id = request_data.get("episode_id")
    episode = await session.get(EpisodeRecord, UUID(str(episode_id))) if episode_id else None
    requested_ids = _request_uuids(task, "scene_ids")
    by_id = {scene.id: scene for scene in existing}

    if image_only:
        config = await require_image_model(session, project.owner_id)
        if requested_ids:
            generated_scenes = [by_id[item] for item in requested_ids if item in by_id]
            if not generated_scenes:
                raise ValueError("指定的场景不存在")
        else:
            generated_scenes = [scene for scene in existing if scene.reference_asset_id is None]
            if not generated_scenes:
                raise ValueError("当前项目没有可生成参考图的场景")
        await session.commit()
        await report_progress(session, task, 45)
    else:
        config = await require_text_model(session, project.owner_id)
        checkpoint = text_checkpoint(task, "scenes")
        if checkpoint is not None:
            checkpoint_ids = [UUID(str(item)) for item in checkpoint.get("scene_ids", [])]
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
            guidance = str(request_data.get("guidance", ""))
            targets = (
                [by_id[item] for item in requested_ids if item in by_id] if requested_ids else None
            )
            if requested_ids and not targets:
                raise ValueError("指定的场景不存在")
            await session.commit()
            await report_progress(session, task, 15)
            cast_mode = _cast_mode(task)
            if targets is not None:
                target_lines = "\n".join(f"- {scene.name}" for scene in targets)
                user_prompt = (
                    f"作品：{title}\n梗概：{synopsis}\n题材：{genre}\n画风：{art_style}\n"
                    f"请只重新设计下列 {len(targets)} 个场景，保持同名场景可辨识：\n"
                    f"{target_lines}\n"
                    f"scenes 数组长度必须为 {len(targets)}，并与上列顺序一致。\n"
                    f'补充要求：{guidance or "无"}\n返回格式：{{"scenes":[{{"name":string,'
                    '"description":string,"lighting":string,"palette":string,'
                    '"visual_traits":[string]}}]}。'
                )
            elif cast_mode == "append" and existing:
                roster_lines = "\n".join(f"- {scene.name}" for scene in existing)
                user_prompt = (
                    f"作品：{title}\n梗概：{synopsis}\n题材：{genre}\n画风：{art_style}\n"
                    "作品已有下列场景，请勿返回他们；仅在本话需要时补充新场景"
                    "（无需新场景则返回空数组）：\n"
                    f"{roster_lines}\n"
                    f'补充要求：{guidance or "无"}\n返回格式：{{"scenes":[{{"name":string,'
                    '"description":string,"lighting":string,"palette":string,'
                    '"visual_traits":[string]}}]}。'
                )
            else:
                user_prompt = (
                    f"作品：{title}\n梗概：{synopsis}\n题材：{genre}\n画风：{art_style}\n"
                    f'补充要求：{guidance or "无"}\n返回格式：{{"scenes":[{{"name":string,'
                    '"description":string,"lighting":string,"palette":string,'
                    '"visual_traits":[string]}}]}。'
                )
            output = await generate_structured_text(
                base_url=config.text_base_url,
                model=config.text_model,
                api_key=text_api_key,
                system_prompt=SCENE_DRAFT.system,
                user_prompt=user_prompt,
                response_model=SceneGenerationOutput,
            )
            await report_progress(session, task, 45)
            if targets is not None:
                if len(output.scenes) != len(targets):
                    raise ValueError("文本模型返回的场景数量不符合请求，请重试")
                generated_scenes = []
                for scene, generated in zip(targets, output.scenes, strict=True):
                    scene.name = generated.name
                    scene.profile = cast(dict[str, object], generated.model_dump(exclude={"name"}))
                    scene.status = "draft"
                    scene.version += 1
                    scene.reference_asset_id = None
                    await session.flush()
                    await clear_image_job(session, task, f"scene:{scene.id}")
                    generated_scenes.append(scene)
            elif cast_mode == "append":
                by_norm = {_normalize_cast_name(scene.name): scene for scene in existing}
                generated_scenes = []
                for generated in output.scenes:
                    key = _normalize_cast_name(generated.name)
                    if key and key in by_norm:
                        continue
                    scene = SceneRecord(
                        project_id=project.id,
                        name=generated.name,
                        profile=cast(dict[str, object], generated.model_dump(exclude={"name"})),
                        status="draft",
                        version=1,
                    )
                    session.add(scene)
                    await session.flush()
                    generated_scenes.append(scene)
                    if key:
                        by_norm[key] = scene
                await session.flush()
            else:
                generated_scenes = []
                for index, generated in enumerate(output.scenes):
                    scene = (
                        existing[index]
                        if index < len(existing)
                        else SceneRecord(project_id=project.id)
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
                kept_ids = {scene.id for scene in generated_scenes}
                removed_ids = {scene.id for scene in existing if scene.id not in kept_ids}
                for scene in existing:
                    if scene.id in removed_ids:
                        await session.delete(scene)
                await _clear_scene_id_from_panels(session, task.project_id, removed_ids)
                await session.flush()
            await persist_text_checkpoint(
                session,
                task,
                "scenes",
                {"scene_ids": [str(scene.id) for scene in generated_scenes]},
            )

    scene_ids = [str(scene.id) for scene in generated_scenes]
    warnings: list[str] = []
    if text_only:
        await report_progress(session, task, 95)
        return {
            "scene_ids": scene_ids,
            "reference_images_generated": 0,
            "warnings": warnings,
            "prompt_template": {"name": SCENE_DRAFT.name, "version": SCENE_DRAFT.version},
        }

    image_api_key_encrypted = getattr(config, "image_api_key_encrypted", None)
    if not image_api_key_encrypted:
        warnings.append("场景文字设定已保存；账户尚未配置图像模型 API Key，因此没有生成参考图。")
    else:
        image_api_key = decrypt_secret(image_api_key_encrypted)
        from app.core.config import get_settings

        image_model = getattr(config, "image_model", None) or get_settings().default_image_model
        image_base_url = getattr(config, "image_base_url", None)
        image_backend = getattr(config, "image_backend", None) or "qwen_async"
        if image_only and requested_ids:
            scenes_to_render = list(generated_scenes)
        else:
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
            await session.commit()
            try:
                await generate_image(
                    api_key=image_api_key,
                    model=image_model,
                    prompt=prompt,
                    asset_id=image_job.asset_id,
                    image_backend=image_backend,
                    base_url=image_base_url,
                    resume_task_id=image_job.resume_task_id,
                    prompt_extend=False,
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
