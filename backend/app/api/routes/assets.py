from uuid import UUID

from fastapi import Depends, Request

from app.api.routes.workspace_common import SessionDep, create_workspace_router
from app.core.security import (
    require_character_owner,
    require_project_owner_dependency,
    require_scene_owner,
)
from app.schemas.workspace import (
    Character,
    CharacterGenerationRequest,
    CharacterPatch,
    GenerationTask,
    Scene,
    SceneGenerationRequest,
    ScenePatch,
)
from app.services import assets as assets_service

router = create_workspace_router(tags=["Characters", "Scenes"])


@router.get(
    "/projects/{project_id}/characters",
    operation_id="listCharacters",
    response_model=list[Character],
    dependencies=[Depends(require_project_owner_dependency)],
)
async def list_characters(project_id: UUID, session: SessionDep) -> list[Character]:
    return await assets_service.list_characters(session, project_id)


@router.patch(
    "/characters/{character_id}",
    operation_id="updateCharacter",
    response_model=Character,
    dependencies=[Depends(require_character_owner)],
)
async def update_character(
    character_id: UUID, body: CharacterPatch, session: SessionDep
) -> Character:
    return await assets_service.update_character(session, character_id, body)


@router.post(
    "/projects/{project_id}/character-generations",
    operation_id="generateCharacters",
    response_model=GenerationTask,
    status_code=202,
    dependencies=[Depends(require_project_owner_dependency)],
)
async def generate_characters(
    project_id: UUID,
    body: CharacterGenerationRequest,
    request: Request,
    session: SessionDep,
) -> GenerationTask:
    return await assets_service.generate_characters(
        session, project_id=project_id, owner_id=request.state.account_id, body=body
    )


@router.get(
    "/projects/{project_id}/scenes",
    operation_id="listScenes",
    response_model=list[Scene],
    dependencies=[Depends(require_project_owner_dependency)],
)
async def list_scenes(project_id: UUID, session: SessionDep) -> list[Scene]:
    return await assets_service.list_scenes(session, project_id)


@router.patch(
    "/scenes/{scene_id}",
    operation_id="updateScene",
    response_model=Scene,
    dependencies=[Depends(require_scene_owner)],
)
async def update_scene(scene_id: UUID, body: ScenePatch, session: SessionDep) -> Scene:
    return await assets_service.update_scene(session, scene_id, body)


@router.post(
    "/projects/{project_id}/scene-generations",
    operation_id="generateScenes",
    response_model=GenerationTask,
    status_code=202,
    dependencies=[Depends(require_project_owner_dependency)],
)
async def generate_scenes(
    project_id: UUID,
    body: SceneGenerationRequest,
    request: Request,
    session: SessionDep,
) -> GenerationTask:
    return await assets_service.generate_scenes(
        session, project_id=project_id, owner_id=request.state.account_id, body=body
    )
