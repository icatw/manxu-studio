from enum import Enum
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import require_rate_limit
from app.core.security import (
    check_csrf,
    current_account_dependency,
)
from app.db.models import AccountRecord, PanelRecord
from app.db.session import get_session
from app.services.generations import create_task, task_view

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


__all__ = [
    "SessionDep",
    "create_task",
    "create_workspace_router",
    "not_found",
    "panel_view",
    "task_view",
]
