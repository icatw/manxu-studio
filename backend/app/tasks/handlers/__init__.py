"""Import handlers so @register decorators populate the registry."""

from app.tasks.handlers import (  # noqa: F401
    characters,
    continue_episode,
    export,
    panel_image,
    scenes,
    story_pipeline,
    storyboard,
)

__all__ = [
    "characters",
    "continue_episode",
    "export",
    "panel_image",
    "scenes",
    "story_pipeline",
    "storyboard",
]
