"""SERIAL-AGENT-01: create next episode + optional storyboard (no chat, no images)."""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.db.models import EpisodeRecord, GenerationTaskRecord, ProjectRecord
from app.schemas.workspace import EpisodeCreate
from app.services.episode_frontier import (
    FrontierCreateNext,
    list_project_episodes_ordered,
    resolve_continue_next,
)
from app.services.projects import create_episode
from app.tasks.handlers.storyboard import generate_panels
from app.tasks.registry import register
from app.tasks.support import report_progress
from app.tasks.types import TaskType


def _stages(task: GenerationTaskRecord) -> dict[str, Any]:
    request_data = task.request_data if isinstance(task.request_data, dict) else {}
    raw = request_data.get("pipeline_stages")
    if not isinstance(raw, dict):
        stages: dict[str, Any] = {}
        request_data["pipeline_stages"] = stages
        task.request_data = request_data
        return stages
    return cast(dict[str, Any], raw)


async def _persist_stage(
    session: AsyncSession,
    task: GenerationTaskRecord,
    stage_name: str,
    payload: dict[str, Any],
) -> None:
    stages = _stages(task)
    stages[stage_name] = {"done": True, **payload}
    try:
        flag_modified(task, "request_data")
    except Exception:
        pass
    await session.commit()


def _stage_done(task: GenerationTaskRecord, stage_name: str) -> dict[str, Any] | None:
    stage = _stages(task).get(stage_name)
    if isinstance(stage, dict) and stage.get("done"):
        return stage
    return None


@register(TaskType.CONTINUE_EPISODE)
async def handle_continue_episode(
    session: AsyncSession, task: GenerationTaskRecord
) -> dict[str, Any]:
    if task.project_id is None:
        raise ValueError("续写任务缺少作品 ID")
    project = await session.get(ProjectRecord, task.project_id)
    if project is None:
        raise ValueError("作品不存在")

    request_data = task.request_data if isinstance(task.request_data, dict) else {}
    generate_storyboard = bool(request_data.get("generate_storyboard", False))
    panel_count_raw = request_data.get("panel_count", 8)
    if not isinstance(panel_count_raw, int) or panel_count_raw < 1:
        raise ValueError("分镜数量无效")
    panel_count = panel_count_raw
    use_continuity = bool(request_data.get("use_continuity", True))
    warnings: list[str] = []
    created = False

    ensure_stage = _stage_done(task, "ensure_episode")
    if ensure_stage is None:
        await report_progress(session, task, 10)
        episodes = await list_project_episodes_ordered(session, task.project_id)
        decision = resolve_continue_next(episodes)
        if not isinstance(decision, FrontierCreateNext):
            raise ValueError(decision.message)
        next_number = len(episodes) + 1
        episode = await create_episode(
            session,
            task.project_id,
            EpisodeCreate(
                title=f"第 {next_number} 话",
                synopsis="待补充本话梗概",
                panel_count=panel_count,
            ),
        )
        created = True
        # create_episode commits; re-attach the generation task.
        refreshed = await session.get(GenerationTaskRecord, task.id)
        if refreshed is None:
            raise ValueError("续写任务丢失")
        task = refreshed
        await _persist_stage(
            session,
            task,
            "ensure_episode",
            {
                "episode_id": str(episode.id),
                "created": True,
                "title": episode.title,
            },
        )
        episode_id = episode.id
        task.episode_id = episode_id
        request_data = dict(task.request_data) if isinstance(task.request_data, dict) else {}
        request_data["episode_id"] = str(episode_id)
        task.request_data = request_data
        try:
            flag_modified(task, "request_data")
        except Exception:
            pass
        await session.commit()
    else:
        episode_id = UUID(str(ensure_stage["episode_id"]))
        created = bool(ensure_stage.get("created", False))
        if task.episode_id is None:
            task.episode_id = episode_id
            await session.commit()

    await report_progress(session, task, 45)

    panel_ids: list[str] = []
    if generate_storyboard:
        storyboard_stage = _stage_done(task, "storyboard")
        if storyboard_stage is None:
            episode_row = await session.get(EpisodeRecord, episode_id)
            if episode_row is None:
                raise ValueError("故事单元不存在")
            # generate_panels reads episode_id / panel_count / use_continuity from request_data.
            request_data = dict(task.request_data) if isinstance(task.request_data, dict) else {}
            request_data["episode_id"] = str(episode_id)
            request_data["panel_count"] = panel_count
            request_data["use_continuity"] = use_continuity
            request_data["pacing"] = request_data.get("pacing", "balanced")
            request_data["use_approved_assets"] = request_data.get("use_approved_assets", True)
            task.request_data = request_data
            try:
                flag_modified(task, "request_data")
            except Exception:
                pass
            await session.commit()
            board_result = await generate_panels(session, task)
            panel_ids = [str(item) for item in board_result.get("panel_ids", [])]
            await _persist_stage(
                session,
                task,
                "storyboard",
                {"episode_id": str(episode_id), "panel_ids": panel_ids},
            )
        else:
            panel_ids = [str(item) for item in storyboard_stage.get("panel_ids", [])]
        await report_progress(session, task, 90)
    else:
        await report_progress(session, task, 85)

    return {
        "episode_id": str(episode_id),
        "created": created,
        "panel_ids": panel_ids,
        "generate_storyboard": generate_storyboard,
        "warnings": warnings,
    }
