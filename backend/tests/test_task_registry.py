from app.tasks.registry import get_handler, registered_types
from app.tasks.types import TaskType


def test_all_task_types_have_handlers() -> None:
    expected = {
        TaskType.CHARACTER_DRAFT,
        TaskType.SCENE_DRAFT,
        TaskType.SCENE_REFERENCE_IMAGES,
        TaskType.STORYBOARD_DRAFT,
        TaskType.STORY_PIPELINE,
        TaskType.PANEL_IMAGE,
        TaskType.PANEL_IMAGE_EDIT,
        TaskType.EXPORT,
    }
    assert registered_types() == expected
    for task_type in expected:
        assert callable(get_handler(task_type))
