from enum import Enum
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import require_rate_limit
from app.core.security import (
    check_csrf,
    current_account_dependency,
)
from app.db.models import AccountRecord, GenerationTaskRecord, PanelRecord
from app.db.session import get_session
from app.schemas.workspace import GenerationTask
from app.services.task_queue import enqueue_generation_task

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def require_workspace_account(
    request: Request,
    account: Annotated[AccountRecord, Depends(current_account_dependency)],
) -> None:
    """Populate account state used by workspace handlers after validating the session."""
    request.state.account_id = account.id
    request.state.account = account


def create_workspace_router(*, tags: list[str | Enum]) -> APIRouter:
    return APIRouter(
        tags=tags,
        dependencies=[
            Depends(require_workspace_account),
            Depends(check_csrf),
            Depends(require_rate_limit),
        ],
    )


def not_found(resource: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{resource}不存在")


def task_view(task: GenerationTaskRecord) -> GenerationTask:
    return GenerationTask.model_validate(task)


def panel_view(panel: PanelRecord) -> dict[str, object]:
    return {
        "id": panel.id,
        "episode_id": panel.episode_id,
        "position": panel.position,
        "scene_description": panel.scene_description,
        "shot": panel.shot,
        "composition": panel.composition,
        "character_actions": panel.character_actions,
        "emotion": panel.emotion,
        "dialogue": panel.dialogue,
        "story_purpose": panel.story_purpose,
        "image_prompt": panel.image_prompt,
        "character_ids": panel.character_ids,
        "scene_id": panel.scene_id,
        "review_status": panel.review_status,
        "current_image_asset_id": panel.current_image_asset_id,
        "version": panel.version,
        "created_at": panel.created_at,
        "updated_at": panel.updated_at,
    }


async def create_task(
    session: AsyncSession,
    background_tasks: BackgroundTasks,
    *,
    owner_id: UUID,
    project_id: UUID,
    task_type: str,
    request_data: dict[str, object],
    episode_id: UUID | None = None,
    panel_id: UUID | None = None,
    retry_of_task_id: UUID | None = None,
    idempotency_key: str | None = None,
) -> GenerationTask:
    if idempotency_key:
        existing = await session.scalar(
            select(GenerationTaskRecord).where(
                GenerationTaskRecord.owner_id == owner_id,
                GenerationTaskRecord.idempotency_key == idempotency_key,
            )
        )
        if existing is not None:
            return task_view(existing)
    task = GenerationTaskRecord(
        owner_id=owner_id,
        project_id=project_id,
        episode_id=episode_id,
        panel_id=panel_id,
        task_type=task_type,
        status="queued",
        progress=0,
        request_data=request_data,
        retry_of_task_id=retry_of_task_id,
        idempotency_key=idempotency_key,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    try:
        await enqueue_generation_task(task.id)
    except Exception as error:
        raise HTTPException(503, "生成队列暂时不可用，任务已保存并将在服务恢复后重试") from error
    return task_view(task)


__all__ = [
    "SessionDep",
    "create_task",
    "create_workspace_router",
    "not_found",
    "panel_view",
    "task_view",
]
