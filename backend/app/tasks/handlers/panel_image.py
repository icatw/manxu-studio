from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_secret
from app.db.models import (
    CharacterRecord,
    GenerationTaskRecord,
    ImageVersionRecord,
    PanelRecord,
    ProjectRecord,
)
from app.providers import generate_image
from app.tasks.provider_jobs import bind_image_job
from app.tasks.registry import register
from app.tasks.support import require_image_model
from app.tasks.types import TaskType


async def generate_panel_image(session: AsyncSession, task: GenerationTaskRecord) -> dict[str, Any]:
    if task.panel_id is None:
        raise ValueError("缺少目标分镜")
    panel = await session.get(PanelRecord, task.panel_id)
    if panel is None:
        raise ValueError("分镜不存在")
    project = await session.get(ProjectRecord, task.project_id)
    if project is None or project.owner_id is None:
        raise ValueError("项目账户归属缺失")
    config = await require_image_model(session, project.owner_id)
    instruction = str(task.request_data.get("instruction", "")).strip()
    locked_character_constraints: list[str] = []
    character_uuids: list[UUID] = []
    for raw_id in panel.character_ids or []:
        try:
            character_uuids.append(UUID(str(raw_id)))
        except ValueError:
            continue
    if character_uuids:
        characters = list(
            (
                await session.scalars(
                    select(CharacterRecord).where(
                        CharacterRecord.project_id == task.project_id,
                        CharacterRecord.id.in_(character_uuids),
                        CharacterRecord.reference_locked.is_(True),
                    )
                )
            ).all()
        )
        for character in characters:
            profile = character.profile if isinstance(character.profile, dict) else {}
            appearance = str(profile.get("appearance") or "").strip()
            image_prompt = str(profile.get("image_prompt") or "").strip()
            parts = [f"角色「{character.name}」保持定妆一致"]
            if appearance:
                parts.append(appearance)
            if image_prompt:
                parts.append(image_prompt)
            if character.reference_asset_id is not None:
                parts.append(f"（已锁定定妆参考图 asset:{character.reference_asset_id}）")
            locked_character_constraints.append("；".join(parts))
    prompt = "\n".join(
        item
        for item in [
            project.art_style,
            project.style_rules,
            panel.scene_description,
            panel.shot,
            panel.composition,
            panel.character_actions,
            panel.emotion,
            *locked_character_constraints,
            instruction,
            project.negative_prompt,
            "无文字、无水印，保持漫画分镜构图",
        ]
        if item
    )
    api_key = decrypt_secret(config.image_api_key_encrypted)
    image_model = config.image_model
    image_base_url = config.image_base_url
    image_job = await bind_image_job(session, task, f"panel:{panel.id}")
    await session.commit()
    image_url = await generate_image(
        api_key=api_key,
        model=image_model,
        prompt=prompt,
        asset_id=image_job.asset_id,
        base_url=image_base_url,
        resume_task_id=image_job.resume_task_id,
        on_submit_started=image_job.on_submit_started,
        on_submit_rejected=image_job.on_submit_rejected,
        on_submitted=image_job.on_submitted,
    )
    version = ImageVersionRecord(
        panel_id=panel.id, asset_id=image_job.asset_id, image_url=image_url
    )
    session.add(version)
    panel.current_image_asset_id = image_job.asset_id
    panel.current_image_url = image_url
    panel.version += 1
    await session.flush()
    return {"panel_id": str(panel.id), "asset_id": str(image_job.asset_id)}


@register(TaskType.PANEL_IMAGE)
async def handle_panel_image(session: AsyncSession, task: GenerationTaskRecord) -> dict[str, Any]:
    return await generate_panel_image(session, task)


@register(TaskType.PANEL_IMAGE_EDIT)
async def handle_panel_image_edit(
    session: AsyncSession, task: GenerationTaskRecord
) -> dict[str, Any]:
    return await generate_panel_image(session, task)
