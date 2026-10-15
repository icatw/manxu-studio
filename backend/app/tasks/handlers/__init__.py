"""Import handlers so @register decorators populate the registry."""

from app.tasks.handlers import (  # noqa: F401
    characters,
    export,
    panel_image,
    scenes,
    story_pipeline,
    storyboard,
)

__all__ = [
    "characters",
    "export",
    "panel_image",
    "scenes",
    "story_pipeline",
    "storyboard",
]
