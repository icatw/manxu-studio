from uuid import UUID

from fastapi import Depends, Query, Request, Response

from app.api.routes.workspace_common import SessionDep, create_workspace_router
from app.core.security import (
    require_asset_owner,
    require_episode_owner,
    require_project_owner_dependency,
    require_task_owner,
)
from app.schemas.workspace import (
    AnthologyExportRequest,
    ExportRequest,
    GenerationProviderResumeRequest,
    GenerationTask,
    ManuscriptExportRequest,
)
from app.services import generations as generations_service

router = create_workspace_router(tags=["Generations", "Exports"])


@router.get(
    "/episodes/{episode_id}/generation-tasks",
    operation_id="listEpisodeGenerationTasks",
    response_model=list[GenerationTask],
    dependencies=[Depends(require_episode_owner)],
)
async def list_episode_generation_tasks(
    episode_id: UUID,
    session: SessionDep,
    active_only: bool = Query(default=True),
) -> list[GenerationTask]:
    return await generations_service.list_episode_tasks(
        session, episode_id=episode_id, active_only=active_only
    )


@router.get(
    "/generation-tasks/{task_id}",
    operation_id="getGenerationTask",
    response_model=GenerationTask,
    dependencies=[Depends(require_task_owner)],
)
async def get_generation_task(task_id: UUID, session: SessionDep) -> GenerationTask:
    return await generations_service.get_task(session, task_id)


@router.post(
    "/generation-tasks/{task_id}/retries",
    operation_id="retryGenerationTask",
    response_model=GenerationTask,
    status_code=202,
    dependencies=[Depends(require_task_owner)],
)
async def retry_generation_task(
    task_id: UUID, request: Request, session: SessionDep
) -> GenerationTask:
    return await generations_service.retry_task(
        session, task_id=task_id, owner_id=request.state.account_id
    )


@router.post(
    "/generation-tasks/{task_id}/provider-resumes",
    operation_id="resumeProviderGenerationTask",
    response_model=GenerationTask,
    status_code=202,
    dependencies=[Depends(require_task_owner)],
)
async def resume_provider_generation_task(
    task_id: UUID,
    body: GenerationProviderResumeRequest,
    session: SessionDep,
) -> GenerationTask:
    return await generations_service.resume_provider_task(session, task_id=task_id, body=body)


@router.post(
    "/episodes/{episode_id}/exports",
    operation_id="createEpisodeExport",
    response_model=GenerationTask,
    status_code=202,
    dependencies=[Depends(require_episode_owner)],
)
async def create_episode_export(
    episode_id: UUID,
    body: ExportRequest,
    request: Request,
    session: SessionDep,
) -> GenerationTask:
    return await generations_service.create_export(
        session, episode_id=episode_id, owner_id=request.state.account_id, body=body
    )


@router.post(
    "/episodes/{episode_id}/manuscript-exports",
    operation_id="createEpisodeManuscriptExport",
    response_model=GenerationTask,
    status_code=202,
    dependencies=[Depends(require_episode_owner)],
)
async def create_episode_manuscript_export(
    episode_id: UUID,
    body: ManuscriptExportRequest,
    request: Request,
    session: SessionDep,
) -> GenerationTask:
    return await generations_service.create_manuscript_export(
        session, episode_id=episode_id, owner_id=request.state.account_id, body=body
    )


@router.post(
    "/projects/{project_id}/exports",
    operation_id="createProjectAnthologyExport",
    response_model=GenerationTask,
    status_code=202,
    dependencies=[Depends(require_project_owner_dependency)],
)
async def create_project_anthology_export(
    project_id: UUID,
    body: AnthologyExportRequest,
    request: Request,
    session: SessionDep,
) -> GenerationTask:
    return await generations_service.create_anthology_export(
        session, project_id=project_id, owner_id=request.state.account_id, body=body
    )


@router.get(
    "/exports/{asset_id}",
    operation_id="downloadExport",
    dependencies=[Depends(require_asset_owner)],
)
async def download_export(asset_id: UUID, session: SessionDep) -> Response:
    return await generations_service.download_export(session, asset_id)


@router.get(
    "/assets/{asset_id}", operation_id="getImageAsset", dependencies=[Depends(require_asset_owner)]
)
async def get_image_asset(asset_id: UUID) -> Response:
    return await generations_service.get_image_asset(asset_id)
