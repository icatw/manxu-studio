from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

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


@register(TaskType.STORY_PIPELINE)
async def handle_story_pipeline(
    session: AsyncSession, task: GenerationTaskRecord
) -> dict[str, Any]:
    """Run character → scene → storyboard as one recoverable server-side workflow."""
    regenerate_characters = bool(task.request_data.get("regenerate_characters", True))
    warnings: list[str] = []
    character_ids: list[str] = []
    scene_ids: list[str] = []

    if regenerate_characters:
        await report_progress(session, task, 5)
        character_result = await generate_characters(session, task)
        character_ids = [str(item) for item in character_result.get("character_ids", [])]
        warnings.extend(_warnings(character_result))
        await report_progress(session, task, 35)
        scene_result = await generate_scenes(session, task, image_only=False)
        scene_ids = [str(item) for item in scene_result.get("scene_ids", [])]
        warnings.extend(_warnings(scene_result))
        await report_progress(session, task, 65)
    else:
        await report_progress(session, task, 40)

    board_result = await generate_panels(session, task)
    await report_progress(session, task, 95)
    return {
        "character_ids": character_ids,
        "scene_ids": scene_ids,
        "episode_id": board_result["episode_id"],
        "panel_ids": board_result["panel_ids"],
        "warnings": warnings,
    }
