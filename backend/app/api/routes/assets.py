from uuid import UUID

from fastapi import BackgroundTasks, Depends, Request
from sqlalchemy import select

from app.api.routes.workspace_common import (
    SessionDep,
    create_workspace_router,
)
from app.api.routes.workspace_common import (
    create_task as _create_task,
)
from app.api.routes.workspace_common import (
    not_found as _not_found,
)
from app.core.security import (
    require_character_owner,
    require_project_owner_dependency,
    require_scene_owner,
)
from app.db.models import (
    CharacterRecord,
    ProjectRecord,
    SceneRecord,
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

router = create_workspace_router(tags=["Characters", "Scenes"])


def _scene_view(record: SceneRecord) -> Scene:
    profile = dict(record.profile)
    profile.pop("name", None)
    return Scene.model_validate(
        {
            "id": record.id,
            "project_id": record.project_id,
            "name": record.name,
            "profile": profile,
            "reference_asset_id": record.reference_asset_id,
            "status": record.status,
            "version": record.version,
        }
    )


@router.get(
    "/projects/{project_id}/characters",
    operation_id="listCharacters",
    response_model=list[Character],
    dependencies=[Depends(require_project_owner_dependency)],
)
async def list_characters(project_id: UUID, session: SessionDep) -> list[Character]:
    if await session.get(ProjectRecord, project_id) is None:
        raise _not_found("项目")
    rows = await session.scalars(
        select(CharacterRecord).where(CharacterRecord.project_id == project_id)
    )
    return [Character.model_validate(item) for item in rows]


@router.patch(
    "/characters/{character_id}",
    operation_id="updateCharacter",
    response_model=Character,
    dependencies=[Depends(require_character_owner)],
)
async def update_character(
    character_id: UUID, body: CharacterPatch, session: SessionDep
) -> Character:
    record = await session.get(CharacterRecord, character_id)
    if record is None:
        raise _not_found("角色")
    values = body.model_dump(exclude_unset=True)
    if "profile" in values and values["profile"] is not None:
        values["profile"] = body.profile.model_dump() if body.profile else None
    for key, value in values.items():
        setattr(record, key, value)
    record.version += 1
    await session.commit()
    await session.refresh(record)
    return Character.model_validate(record)


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
    background_tasks: BackgroundTasks,
    session: SessionDep,
) -> GenerationTask:
    if await session.get(ProjectRecord, project_id) is None:
        raise _not_found("项目")
    return await _create_task(
        session,
        background_tasks,
        owner_id=request.state.account_id,
        project_id=project_id,
        task_type="character_draft",
        request_data=body.model_dump(mode="json"),
    )


@router.get(
    "/projects/{project_id}/scenes",
    operation_id="listScenes",
    response_model=list[Scene],
    dependencies=[Depends(require_project_owner_dependency)],
)
async def list_scenes(project_id: UUID, session: SessionDep) -> list[Scene]:
    if await session.get(ProjectRecord, project_id) is None:
        raise _not_found("项目")
    rows = await session.scalars(select(SceneRecord).where(SceneRecord.project_id == project_id))
    return [_scene_view(item) for item in rows]


@router.patch(
    "/scenes/{scene_id}",
    operation_id="updateScene",
    response_model=Scene,
    dependencies=[Depends(require_scene_owner)],
)
async def update_scene(scene_id: UUID, body: ScenePatch, session: SessionDep) -> Scene:
    record = await session.get(SceneRecord, scene_id)
    if record is None:
        raise _not_found("场景")
    values = body.model_dump(exclude_unset=True)
    if "profile" in values and values["profile"] is not None:
        values["profile"] = body.profile.model_dump() if body.profile else None
    for key, value in values.items():
        setattr(record, key, value)
    record.version += 1
    await session.commit()
    await session.refresh(record)
    return _scene_view(record)


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
    background_tasks: BackgroundTasks,
    session: SessionDep,
) -> GenerationTask:
    if await session.get(ProjectRecord, project_id) is None:
        raise _not_found("项目")
    return await _create_task(
        session,
        background_tasks,
        owner_id=request.state.account_id,
        project_id=project_id,
        task_type="scene_reference_images" if body.image_only else "scene_draft",
        request_data=body.model_dump(mode="json"),
    )
