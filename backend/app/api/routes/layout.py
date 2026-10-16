from uuid import UUID

from fastapi import Depends

from app.api.routes.workspace_common import SessionDep, create_workspace_router
from app.core.security import require_episode_owner, require_page_owner, require_slot_owner
from app.schemas.workspace import (
    BootstrapLayoutRequest,
    EpisodeLayout,
    LayoutPage,
    LayoutPreview,
    PageOrder,
    PageSlot,
    PageSlotPatch,
    SlotOrder,
    SyncLayoutRequest,
)
from app.services import layout as layout_service

router = create_workspace_router(tags=["Layout"])


@router.get(
    "/episodes/{episode_id}/layout",
    operation_id="getEpisodeLayout",
    response_model=EpisodeLayout,
    dependencies=[Depends(require_episode_owner)],
)
async def get_episode_layout(episode_id: UUID, session: SessionDep) -> EpisodeLayout:
    return await layout_service.get_episode_layout(episode_id, session)


@router.post(
    "/episodes/{episode_id}/layout/bootstrap",
    operation_id="bootstrapEpisodeLayout",
    response_model=EpisodeLayout,
    status_code=201,
    dependencies=[Depends(require_episode_owner)],
)
async def bootstrap_episode_layout(
    episode_id: UUID,
    session: SessionDep,
    body: BootstrapLayoutRequest | None = None,
) -> EpisodeLayout:
    return await layout_service.bootstrap_episode_layout(episode_id, body, session)


@router.post(
    "/episodes/{episode_id}/layout/sync",
    operation_id="syncEpisodeLayout",
    response_model=EpisodeLayout,
    dependencies=[Depends(require_episode_owner)],
)
async def sync_episode_layout(
    episode_id: UUID,
    session: SessionDep,
    body: SyncLayoutRequest | None = None,
) -> EpisodeLayout:
    return await layout_service.sync_episode_layout(episode_id, body, session)


@router.get(
    "/episodes/{episode_id}/layout/preview",
    operation_id="getEpisodeLayoutPreview",
    response_model=LayoutPreview,
    dependencies=[Depends(require_episode_owner)],
)
async def get_episode_layout_preview(episode_id: UUID, session: SessionDep) -> LayoutPreview:
    return await layout_service.get_episode_layout_preview(episode_id, session)


@router.put(
    "/episodes/{episode_id}/pages/order",
    operation_id="reorderPages",
    response_model=EpisodeLayout,
    dependencies=[Depends(require_episode_owner)],
)
async def reorder_pages(episode_id: UUID, body: PageOrder, session: SessionDep) -> EpisodeLayout:
    return await layout_service.reorder_pages(episode_id, body, session)


@router.put(
    "/pages/{page_id}/slots/order",
    operation_id="reorderPageSlots",
    response_model=LayoutPage,
    dependencies=[Depends(require_page_owner)],
)
async def reorder_page_slots(page_id: UUID, body: SlotOrder, session: SessionDep) -> LayoutPage:
    return await layout_service.reorder_page_slots(page_id, body, session)


@router.patch(
    "/slots/{slot_id}",
    operation_id="updatePageSlot",
    response_model=PageSlot,
    dependencies=[Depends(require_slot_owner)],
)
async def update_page_slot(slot_id: UUID, body: PageSlotPatch, session: SessionDep) -> PageSlot:
    return await layout_service.update_page_slot(slot_id, body, session)
