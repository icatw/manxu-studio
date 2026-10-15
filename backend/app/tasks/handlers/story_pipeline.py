from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.db.models import GenerationTaskRecord
from app.tasks.handlers.characters import generate_characters
from app.tasks.handlers.scenes import generate_scenes
from app.tasks.handlers.storyboard import generate_panels
from app.tasks.registry import register
from app.tasks.support import report_progress
from app.tasks.types import TaskType


def _warnings(result: dict[str, Any]) -> list[str]:
    raw = result.get("warnings")
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, str)]


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


@register(TaskType.STORY_PIPELINE)
async def handle_story_pipeline(
    session: AsyncSession, task: GenerationTaskRecord
) -> dict[str, Any]:
    """Run character → scene → storyboard with per-stage resume checkpoints."""
    regenerate_characters = bool(task.request_data.get("regenerate_characters", True))
    warnings: list[str] = []
    character_ids: list[str] = []
    scene_ids: list[str] = []

    if regenerate_characters:
        characters_stage = _stage_done(task, "characters")
        if characters_stage is None:
            await report_progress(session, task, 5)
            character_result = await generate_characters(session, task)
            character_ids = [str(item) for item in character_result.get("character_ids", [])]
            stage_warnings = _warnings(character_result)
            warnings.extend(stage_warnings)
            await _persist_stage(
                session,
                task,
                "characters",
                {"character_ids": character_ids, "warnings": stage_warnings},
            )
        else:
            character_ids = [str(item) for item in characters_stage.get("character_ids", [])]
            warnings.extend(_warnings(characters_stage))

        await report_progress(session, task, 35)
        scenes_stage = _stage_done(task, "scenes")
        if scenes_stage is None:
            scene_result = await generate_scenes(session, task, image_only=False)
            scene_ids = [str(item) for item in scene_result.get("scene_ids", [])]
            stage_warnings = _warnings(scene_result)
            warnings.extend(stage_warnings)
            await _persist_stage(
                session,
                task,
                "scenes",
                {"scene_ids": scene_ids, "warnings": stage_warnings},
            )
        else:
            scene_ids = [str(item) for item in scenes_stage.get("scene_ids", [])]
            warnings.extend(_warnings(scenes_stage))
        await report_progress(session, task, 65)
    else:
        await report_progress(session, task, 40)

    storyboard_stage = _stage_done(task, "storyboard")
    if storyboard_stage is None:
        board_result = await generate_panels(session, task)
        await _persist_stage(
            session,
            task,
            "storyboard",
            {
                "episode_id": board_result["episode_id"],
                "panel_ids": board_result["panel_ids"],
            },
        )
        episode_id = board_result["episode_id"]
        panel_ids = board_result["panel_ids"]
    else:
        episode_id = str(storyboard_stage.get("episode_id", ""))
        panel_ids = [str(item) for item in storyboard_stage.get("panel_ids", [])]

    await report_progress(session, task, 95)
    return {
        "character_ids": character_ids,
        "scene_ids": scene_ids,
        "episode_id": episode_id,
        "panel_ids": panel_ids,
        "warnings": warnings,
    }
