from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import GenerationTaskRecord
from app.tasks.types import TaskType

TaskHandler = Callable[[AsyncSession, GenerationTaskRecord], Awaitable[dict[str, Any]]]

_HANDLERS: dict[TaskType, TaskHandler] = {}


def register(task_type: TaskType) -> Callable[[TaskHandler], TaskHandler]:
    def decorator(handler: TaskHandler) -> TaskHandler:
        if task_type in _HANDLERS:
            raise ValueError(f"Task handler already registered: {task_type}")
        _HANDLERS[task_type] = handler
        return handler

    return decorator


def get_handler(task_type: str) -> TaskHandler:
    try:
        key = TaskType(task_type)
    except ValueError as error:
        raise ValueError(f"不支持的任务类型：{task_type}") from error
    handler = _HANDLERS.get(key)
    if handler is None:
        raise ValueError(f"不支持的任务类型：{task_type}")
    return handler


def registered_types() -> frozenset[TaskType]:
    return frozenset(_HANDLERS)
