"""Compatibility façade over the tasks package.

Prefer importing from `app.tasks` / `app.tasks.handlers` in new code.
"""

from app.core.security import decrypt_secret
from app.providers import generate_image as generate_qwen_image
from app.providers import generate_structured_text
from app.tasks.handlers.characters import generate_characters as _generate_characters
from app.tasks.handlers.export import handle_export as _create_export
from app.tasks.handlers.export import render_png as _render_png
from app.tasks.handlers.panel_image import generate_panel_image as _generate_panel_image
from app.tasks.handlers.scenes import generate_scenes as _generate_scenes
from app.tasks.handlers.storyboard import generate_panels as _generate_panels
from app.tasks.registry import get_handler
from app.tasks.runtime import run_generation_task
from app.tasks.schemas import (
    CharacterGenerationOutput,
    GeneratedCharacter,
    GeneratedPanel,
    GeneratedScene,
    SceneGenerationOutput,
    StoryboardGenerationOutput,
)
from app.tasks.support import report_progress as _report_progress
from app.tasks.support import require_text_model as _configured_model


async def _process_task(session, task):  # type: ignore[no-untyped-def]
    handler = get_handler(task.task_type)
    return await handler(session, task)


__all__ = [
    "CharacterGenerationOutput",
    "GeneratedCharacter",
    "GeneratedPanel",
    "GeneratedScene",
    "SceneGenerationOutput",
    "StoryboardGenerationOutput",
    "_configured_model",
    "_create_export",
    "_generate_characters",
    "_generate_panels",
    "_generate_panel_image",
    "_generate_scenes",
    "_process_task",
    "_render_png",
    "_report_progress",
    "decrypt_secret",
    "generate_qwen_image",
    "generate_structured_text",
    "run_generation_task",
]
