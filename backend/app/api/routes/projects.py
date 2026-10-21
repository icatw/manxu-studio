from typing import Annotated
from uuid import UUID

from fastapi import Depends, Query, Request, Response

from app.api.routes.workspace_common import SessionDep, create_workspace_router
from app.core.security import require_episode_owner, require_project_owner_dependency
from app.schemas.workspace import (
    AnthologyPreview,
    ContinueEpisodeRequest,
    Episode,
    EpisodeCreate,
    EpisodePatch,
    GenerationTask,
    Project,
    ProjectCreate,
    ProjectPage,
    ProjectPatch,
    ProjectUpdateResult,
)
from app.services import anthology as anthology_service
from app.services import projects as projects_service
from app.services import storyboard as storyboard_service

router = create_workspace_router(tags=["Projects", "Episodes"])


@router.get("/projects", operation_id="listProjects", response_model=ProjectPage)
async def list_projects(
    request: Request,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: UUID | None = None,
) -> ProjectPage:
    return await projects_service.list_projects(
        session, owner_id=request.state.account_id, limit=limit, cursor=cursor
    )


@router.post("/projects", operation_id="createProject", response_model=Project, status_code=201)
async def create_project(body: ProjectCreate, request: Request, session: SessionDep) -> Project:
    return await projects_service.create_project(
        session, owner_id=request.state.account_id, body=body
    )


@router.get(
    "/projects/{project_id}",
    operation_id="getProject",
    response_model=Project,
    dependencies=[Depends(require_project_owner_dependency)],
)
async def get_project(project_id: UUID, session: SessionDep) -> Project:
    return await projects_service.get_project(session, project_id)


@router.patch(
    "/projects/{project_id}",
    operation_id="updateProject",
    response_model=ProjectUpdateResult,
    dependencies=[Depends(require_project_owner_dependency)],
)
async def update_project(
    project_id: UUID, body: ProjectPatch, session: SessionDep
) -> ProjectUpdateResult:
    return await projects_service.update_project(session, project_id, body)


@router.delete(
    "/projects/{project_id}",
    operation_id="deleteProject",
    status_code=204,
    dependencies=[Depends(require_project_owner_dependency)],
)
async def delete_project(project_id: UUID, session: SessionDep) -> Response:
    await projects_service.delete_project(session, project_id)
    return Response(status_code=204)


@router.get(
    "/projects/{project_id}/episodes",
    operation_id="listEpisodes",
    response_model=list[Episode],
    dependencies=[Depends(require_project_owner_dependency)],
)
async def list_episodes(project_id: UUID, session: SessionDep) -> list[Episode]:
    return await projects_service.list_episodes(session, project_id)


@router.get(
    "/projects/{project_id}/anthology/preview",
    operation_id="getProjectAnthologyPreview",
    response_model=AnthologyPreview,
    dependencies=[Depends(require_project_owner_dependency)],
)
async def get_project_anthology_preview(
    project_id: UUID,
    session: SessionDep,
    episode_ids: Annotated[list[UUID], Query(min_length=1, max_length=40)],
) -> AnthologyPreview:
    return await anthology_service.get_project_anthology_preview(
        session, project_id=project_id, episode_ids=episode_ids
    )


@router.post(
    "/projects/{project_id}/episodes",
    operation_id="createEpisode",
    response_model=Episode,
    status_code=201,
    dependencies=[Depends(require_project_owner_dependency)],
)
async def create_episode(project_id: UUID, body: EpisodeCreate, session: SessionDep) -> Episode:
    return await projects_service.create_episode(session, project_id, body)


@router.post(
    "/projects/{project_id}/continue-episode-generations",
    operation_id="continueEpisodeGeneration",
    response_model=GenerationTask,
    status_code=202,
    dependencies=[Depends(require_project_owner_dependency)],
)
async def continue_episode_generation(
    project_id: UUID,
    body: ContinueEpisodeRequest,
    request: Request,
    session: SessionDep,
) -> GenerationTask:
    return await storyboard_service.continue_episode_generation(
        session,
        project_id=project_id,
        owner_id=request.state.account_id,
        body=body,
    )


@router.patch(
    "/episodes/{episode_id}",
    operation_id="updateEpisode",
    response_model=Episode,
    dependencies=[Depends(require_episode_owner)],
)
async def update_episode(episode_id: UUID, body: EpisodePatch, session: SessionDep) -> Episode:
    return await projects_service.update_episode(session, episode_id, body)
