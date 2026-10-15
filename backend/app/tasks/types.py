from enum import StrEnum
from typing import TypedDict


class TaskType(StrEnum):
    CHARACTER_DRAFT = "character_draft"
    SCENE_DRAFT = "scene_draft"
    SCENE_REFERENCE_IMAGES = "scene_reference_images"
    STORYBOARD_DRAFT = "storyboard_draft"
    STORY_PIPELINE = "story_pipeline"
    PANEL_IMAGE = "panel_image"
    PANEL_IMAGE_EDIT = "panel_image_edit"
    EXPORT = "export"


class TaskFailure(TypedDict):
    code: str
    message: str


TASK_FAILURES: dict[TaskType, TaskFailure] = {
    TaskType.PANEL_IMAGE: {
        "code": "PROVIDER_ERROR",
        "message": "图像生成失败，请检查模型配置后重试",
    },
    TaskType.PANEL_IMAGE_EDIT: {
        "code": "PROVIDER_ERROR",
        "message": "图像生成失败，请检查模型配置后重试",
    },
}

DEFAULT_TASK_FAILURE: TaskFailure = {
    "code": "TASK_FAILED",
    "message": "任务执行失败，请稍后重试",
}


def failure_for(task_type: str) -> TaskFailure:
    try:
        return TASK_FAILURES.get(TaskType(task_type), DEFAULT_TASK_FAILURE)
    except ValueError:
        return DEFAULT_TASK_FAILURE
