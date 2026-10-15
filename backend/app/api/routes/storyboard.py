from uuid import UUID

from fastapi import Depends, Request, Response

from app.api.routes.workspace_common import SessionDep, create_workspace_router
from app.core.security import (
    require_episode_owner,
    require_panel_owner,
    require_project_owner_dependency,
)
from app.schemas.workspace import (
    GenerationTask,
    PanelImageGenerationRequest,
    PanelImageVersion,
    PanelOrder,
    StoryboardGenerationRequest,
    StoryboardPanel,
    StoryboardPanelCreate,
    StoryboardPanelPatch,
    StoryPipelineRequest,
)
from app.services import storyboard as storyboard_service

router = create_workspace_router(tags=["Storyboards"])


@router.post(
    "/projects/{project_id}/storyboard-generations",
    operation_id="generateStoryboard",
    response_model=GenerationTask,
    status_code=202,
    dependencies=[Depends(require_project_owner_dependency)],
)
async def generate_storyboard(
    project_id: UUID,
    body: StoryboardGenerationRequest,
    request: Request,
    session: SessionDep,
) -> GenerationTask:
    return await storyboard_service.generate_storyboard(
        session, project_id=project_id, owner_id=request.state.account_id, body=body
    )


@router.post(
    "/projects/{project_id}/story-generations",
    operation_id="generateStoryPipeline",
    response_model=GenerationTask,
    status_code=202,
    dependencies=[Depends(require_project_owner_dependency)],
)
async def generate_story_pipeline(
    project_id: UUID,
    body: StoryPipelineRequest,
    request: Request,
    session: SessionDep,
) -> GenerationTask:
    return await storyboard_service.generate_story_pipeline(
        session, project_id=project_id, owner_id=request.state.account_id, body=body
    )


@router.get(
    "/episodes/{episode_id}/panels",
    operation_id="listPanels",
    response_model=list[StoryboardPanel],
    dependencies=[Depends(require_episode_owner)],
)
async def list_panels(episode_id: UUID, session: SessionDep) -> list[StoryboardPanel]:
    return await storyboard_service.list_panels(episode_id, session)


@router.post(
    "/episodes/{episode_id}/panels",
    operation_id="createPanel",
    response_model=StoryboardPanel,
    status_code=201,
    dependencies=[Depends(require_episode_owner)],
)
async def create_panel(
    episode_id: UUID, body: StoryboardPanelCreate, session: SessionDep
) -> StoryboardPanel:
    return await storyboard_service.create_panel(episode_id, body, session)


@router.put(
    "/episodes/{episode_id}/panels/order",
    operation_id="reorderPanels",
    response_model=list[StoryboardPanel],
    dependencies=[Depends(require_episode_owner)],
)
async def reorder_panels(
    episode_id: UUID, body: PanelOrder, session: SessionDep
) -> list[StoryboardPanel]:
    return await storyboard_service.reorder_panels(episode_id, body, session)


@router.patch(
    "/panels/{panel_id}",
    operation_id="updatePanel",
    response_model=StoryboardPanel,
    dependencies=[Depends(require_panel_owner)],
)
async def update_panel(
    panel_id: UUID, body: StoryboardPanelPatch, session: SessionDep
) -> StoryboardPanel:
    return await storyboard_service.update_panel(panel_id, body, session)


@router.delete(
    "/panels/{panel_id}",
    operation_id="deletePanel",
    status_code=204,
    dependencies=[Depends(require_panel_owner)],
)
async def delete_panel(panel_id: UUID, session: SessionDep) -> Response:
    return await storyboard_service.delete_panel(panel_id, session)


@router.post(
    "/panels/{panel_id}/image-generations",
    operation_id="generatePanelImage",
    response_model=GenerationTask,
    status_code=202,
    dependencies=[Depends(require_panel_owner)],
)
async def generate_panel_image(
    panel_id: UUID,
    body: PanelImageGenerationRequest,
    request: Request,
    session: SessionDep,
) -> GenerationTask:
    return await storyboard_service.generate_panel_image(
        session, panel_id=panel_id, owner_id=request.state.account_id, body=body
    )


@router.get(
    "/panels/{panel_id}/image-versions",
    operation_id="listPanelImageVersions",
    response_model=list[PanelImageVersion],
    dependencies=[Depends(require_panel_owner)],
)
async def list_panel_image_versions(panel_id: UUID, session: SessionDep) -> list[PanelImageVersion]:
    return await storyboard_service.list_panel_image_versions(panel_id, session)


@router.put(
    "/panels/{panel_id}/image-versions/{version_id}/selection",
    operation_id="selectPanelImageVersion",
    response_model=PanelImageVersion,
    dependencies=[Depends(require_panel_owner)],
)
async def select_panel_image_version(
    panel_id: UUID, version_id: UUID, session: SessionDep
) -> PanelImageVersion:
    return await storyboard_service.select_panel_image_version(panel_id, version_id, session)
