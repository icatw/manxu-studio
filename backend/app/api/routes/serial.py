from datetime import UTC, datetime
from uuid import UUID

from fastapi import Depends, HTTPException, Query, Request, Response
from sqlalchemy import select

from app.api.routes.workspace_common import SessionDep, create_workspace_router
from app.api.routes.workspace_common import not_found as _not_found
from app.core.security import require_episode_owner, require_project_owner_dependency
from app.db.models import EpisodeRecord, PlotThreadRecord, ProjectRecord
from app.schemas.workspace import (
    EpisodeReader,
    EpisodeSummaryResult,
    PlotThread,
    PlotThreadCreate,
    PlotThreadPatch,
    ProjectContinuity,
    ProjectFromPlanCreate,
    ProjectFromPlanResult,
    ProjectPlanDraft,
    ProjectPlanRequest,
)
from app.services import serial_service
from app.services.projects import project_view as _project_view

router = create_workspace_router(tags=["Serial"])


@router.post(
    "/projects/plan",
    operation_id="planProject",
    response_model=ProjectPlanDraft,
)
async def plan_project(
    body: ProjectPlanRequest, request: Request, session: SessionDep
) -> ProjectPlanDraft:
    try:
        return await serial_service.plan_project(session, request.state.account_id, body)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post(
    "/projects/from-plan",
    operation_id="createProjectFromPlan",
    response_model=ProjectFromPlanResult,
    status_code=201,
)
async def create_project_from_plan(
    body: ProjectFromPlanCreate, request: Request, session: SessionDep
) -> ProjectFromPlanResult:
    result = await serial_service.create_project_from_plan(session, request.state.account_id, body)
    record = await session.get(ProjectRecord, result.project.id)
    if record is None:
        raise _not_found("项目")
    result.project = await _project_view(session, record)
    return result


@router.get(
    "/projects/{project_id}/continuity",
    operation_id="getProjectContinuity",
    response_model=ProjectContinuity,
    dependencies=[Depends(require_project_owner_dependency)],
)
async def get_project_continuity(
    project_id: UUID,
    session: SessionDep,
    before_position: int | None = Query(default=None, ge=0),
) -> ProjectContinuity:
    if await session.get(ProjectRecord, project_id) is None:
        raise _not_found("项目")
    return await serial_service.build_continuity(
        session, project_id, before_position=before_position
    )


@router.get(
    "/projects/{project_id}/plot-threads",
    operation_id="listPlotThreads",
    response_model=list[PlotThread],
    dependencies=[Depends(require_project_owner_dependency)],
)
async def list_plot_threads(project_id: UUID, session: SessionDep) -> list[PlotThread]:
    if await session.get(ProjectRecord, project_id) is None:
        raise _not_found("项目")
    rows = await session.scalars(
        select(PlotThreadRecord)
        .where(PlotThreadRecord.project_id == project_id)
        .order_by(PlotThreadRecord.created_at)
    )
    return [PlotThread.model_validate(row) for row in rows]


@router.post(
    "/projects/{project_id}/plot-threads",
    operation_id="createPlotThread",
    response_model=PlotThread,
    status_code=201,
    dependencies=[Depends(require_project_owner_dependency)],
)
async def create_plot_thread(
    project_id: UUID, body: PlotThreadCreate, session: SessionDep
) -> PlotThread:
    if await session.get(ProjectRecord, project_id) is None:
        raise _not_found("项目")
    record = PlotThreadRecord(project_id=project_id, **body.model_dump())
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return PlotThread.model_validate(record)


@router.patch(
    "/plot-threads/{thread_id}",
    operation_id="updatePlotThread",
    response_model=PlotThread,
)
async def update_plot_thread(
    thread_id: UUID, body: PlotThreadPatch, request: Request, session: SessionDep
) -> PlotThread:
    record = await session.get(PlotThreadRecord, thread_id)
    if record is None:
        raise _not_found("伏笔")
    project = await session.get(ProjectRecord, record.project_id)
    if project is None or project.owner_id != request.state.account_id:
        raise _not_found("伏笔")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    record.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(record)
    return PlotThread.model_validate(record)


@router.delete(
    "/plot-threads/{thread_id}",
    operation_id="deletePlotThread",
    status_code=204,
)
async def delete_plot_thread(thread_id: UUID, request: Request, session: SessionDep) -> Response:
    record = await session.get(PlotThreadRecord, thread_id)
    if record is None:
        raise _not_found("伏笔")
    project = await session.get(ProjectRecord, record.project_id)
    if project is None or project.owner_id != request.state.account_id:
        raise _not_found("伏笔")
    await session.delete(record)
    await session.commit()
    return Response(status_code=204)


@router.post(
    "/episodes/{episode_id}/summary",
    operation_id="generateEpisodeSummary",
    response_model=EpisodeSummaryResult,
    dependencies=[Depends(require_episode_owner)],
)
async def generate_episode_summary(episode_id: UUID, session: SessionDep) -> EpisodeSummaryResult:
    if await session.get(EpisodeRecord, episode_id) is None:
        raise _not_found("故事单元")
    try:
        return await serial_service.generate_episode_summary(session, episode_id)
    except ValueError as error:
        raise _not_found(str(error)) from error


@router.get(
    "/episodes/{episode_id}/reader",
    operation_id="getEpisodeReader",
    response_model=EpisodeReader,
    dependencies=[Depends(require_episode_owner)],
)
async def get_episode_reader(episode_id: UUID, session: SessionDep) -> EpisodeReader:
    if await session.get(EpisodeRecord, episode_id) is None:
        raise _not_found("故事单元")
    return await serial_service.build_episode_reader(session, episode_id)
