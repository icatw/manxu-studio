from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_secret
from app.db.models import (
    CharacterRecord,
    EpisodeRecord,
    GenerationTaskRecord,
    PanelRecord,
    ProjectRecord,
    SceneRecord,
)
from app.providers import generate_structured_text
from app.tasks.prompts import STORYBOARD_DRAFT
from app.tasks.registry import register
from app.tasks.schemas import StoryboardGenerationOutput
from app.tasks.support import report_progress, require_text_model
from app.tasks.types import TaskType


@register(TaskType.STORYBOARD_DRAFT)
async def handle_storyboard_draft(
    session: AsyncSession, task: GenerationTaskRecord
) -> dict[str, Any]:
    return await generate_panels(session, task)


async def generate_panels(session: AsyncSession, task: GenerationTaskRecord) -> dict[str, Any]:
    episode_id = UUID(str(task.request_data["episode_id"]))
    episode = await session.get(EpisodeRecord, episode_id)
    if episode is None:
        raise ValueError("故事单元不存在")
    requested_count = task.request_data.get("panel_count", 4)
    if not isinstance(requested_count, int):
        raise ValueError("分镜数量必须是整数")
    count = requested_count
    characters = list(
        (
            await session.scalars(
                select(CharacterRecord).where(CharacterRecord.project_id == task.project_id)
            )
        ).all()
    )
    scenes = list(
        (
            await session.scalars(
                select(SceneRecord).where(SceneRecord.project_id == task.project_id)
            )
        ).all()
    )
    existing = list(
        (
            await session.scalars(select(PanelRecord).where(PanelRecord.episode_id == episode_id))
        ).all()
    )
    project = await session.get(ProjectRecord, task.project_id)
    if project is None:
        raise ValueError("项目不存在")
    config = await require_text_model(session, project.owner_id)
    text_api_key = decrypt_secret(config.text_api_key_encrypted)
    title, genre, art_style = project.title, project.genre, project.art_style
    synopsis = episode.synopsis
    world_setting = project.world_setting
    character_context = [{"name": item.name, **item.profile} for item in characters]
    scene_context = [{"name": item.name, **item.profile} for item in scenes]
    pacing = str(task.request_data.get("pacing", "balanced"))
    continuity_block = ""
    if bool(task.request_data.get("use_continuity", True)):
        from app.services.serial_service import build_continuity

        continuity = await build_continuity(session, task.project_id)
        continuity_block = (
            f"世界观：{continuity.world_setting or world_setting}\n"
            f"前情摘要：{[item.model_dump() for item in continuity.previous_summaries]}\n"
            f"未回收伏笔：{[item.model_dump() for item in continuity.open_threads]}\n"
        )
    await session.commit()
    await report_progress(session, task, 15)
    output = await generate_structured_text(
        base_url=config.text_base_url,
        model=config.text_model,
        api_key=text_api_key,
        system_prompt=STORYBOARD_DRAFT.system,
        user_prompt=(
            f"作品：{title}\n题材：{genre}\n画风：{art_style}\n梗概：{synopsis}\n"
            f"{continuity_block}"
            f"分镜数：{count}\n节奏：{pacing}\n角色资产：{character_context}\n场景资产：{scene_context}\n"
            '返回格式：{"panels":[{"shot":string,"scene_description":string,'
            '"composition":string,"character_actions":string,"emotion":string,'
            '"dialogue":string,"story_purpose":string,"image_prompt":string,'
            '"scene_name":string}]}。panels 数量必须与分镜数完全一致。'
        ),
        response_model=StoryboardGenerationOutput,
    )
    await report_progress(session, task, 85)
    if len(output.panels) != count:
        raise ValueError("文本模型返回的分镜数量不符合请求，请重试")
    for item in existing:
        await session.delete(item)
    await session.flush()
    panels: list[PanelRecord] = []
    primary_character_ids = [str(item.id) for item in characters[:1]]
    for position, generated in enumerate(output.panels):
        scene = next((item for item in scenes if item.name == generated.scene_name), None)
        if scene is None and scenes:
            scene = scenes[0]
        panel = PanelRecord(
            episode_id=episode_id,
            position=position,
            scene_description=generated.scene_description,
            shot=generated.shot,
            composition=generated.composition,
            character_actions=generated.character_actions,
            emotion=generated.emotion,
            dialogue=generated.dialogue,
            story_purpose=generated.story_purpose,
            image_prompt=generated.image_prompt,
            character_ids=primary_character_ids,
            scene_id=scene.id if scene else None,
            review_status="draft",
            version=1,
        )
        session.add(panel)
        panels.append(panel)
    await session.flush()
    return {
        "episode_id": str(episode_id),
        "panel_ids": [str(panel.id) for panel in panels],
        "prompt_template": {
            "name": STORYBOARD_DRAFT.name,
            "version": STORYBOARD_DRAFT.version,
        },
    }
