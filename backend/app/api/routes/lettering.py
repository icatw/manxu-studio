from uuid import UUID

from fastapi import Depends, Response

from app.api.routes.workspace_common import SessionDep, create_workspace_router
from app.core.security import require_episode_owner, require_lettering_owner, require_slot_owner
from app.schemas.workspace import (
    EpisodeLayout,
    LetteringObject,
    LetteringObjectCreate,
    LetteringObjectPatch,
    SeedLetteringRequest,
)
from app.services import lettering as lettering_service

router = create_workspace_router(tags=["Lettering"])


@router.post(
    "/episodes/{episode_id}/layout/lettering/seed",
    operation_id="seedLetteringFromDialogue",
    response_model=EpisodeLayout,
    dependencies=[Depends(require_episode_owner)],
)
async def seed_lettering_from_dialogue(
    episode_id: UUID,
    session: SessionDep,
    body: SeedLetteringRequest | None = None,
) -> EpisodeLayout:
    return await lettering_service.seed_lettering_from_dialogue(episode_id, body, session)


@router.post(
    "/slots/{slot_id}/lettering",
    operation_id="createLetteringObject",
    response_model=LetteringObject,
    status_code=201,
    dependencies=[Depends(require_slot_owner)],
)
async def create_lettering_object(
    slot_id: UUID,
    body: LetteringObjectCreate,
    session: SessionDep,
) -> LetteringObject:
    return await lettering_service.create_lettering(slot_id, body, session)


@router.patch(
    "/lettering/{lettering_id}",
    operation_id="updateLetteringObject",
    response_model=LetteringObject,
    dependencies=[Depends(require_lettering_owner)],
)
async def update_lettering_object(
    lettering_id: UUID,
    body: LetteringObjectPatch,
    session: SessionDep,
) -> LetteringObject:
    return await lettering_service.update_lettering(lettering_id, body, session)


@router.delete(
    "/lettering/{lettering_id}",
    operation_id="deleteLetteringObject",
    status_code=204,
    dependencies=[Depends(require_lettering_owner)],
)
async def delete_lettering_object(lettering_id: UUID, session: SessionDep) -> Response:
    await lettering_service.delete_lettering(lettering_id, session)
    return Response(status_code=204)
