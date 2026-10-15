from datetime import UTC, datetime
from uuid import UUID

from fastapi import Depends, Query, Request, Response
from sqlalchemy import select

from app.api.routes.workspace_common import (
    SessionDep,
    create_workspace_router,
)
from app.api.routes.workspace_common import (
    not_found as _not_found,
)
from app.core.security import (
    require_episode_owner,
    require_project_owner_dependency,
)
from app.db.models import (
    EpisodeRecord,
    PanelRecord,
    ProjectRecord,
)
from app.schemas.workspace import (
    Episode,
    EpisodeCreate,
    EpisodePatch,
    Project,
    ProjectCreate,
    ProjectPage,
    ProjectPatch,
)

router = create_workspace_router(tags=["Projects", "Episodes"])


async def _project_cover_image_url(session: SessionDep, record: ProjectRecord) -> str | None:
    if record.cover_asset_id is not None:
        return f"/api/v1/assets/{record.cover_asset_id}"
    image_url = await session.scalar(
        select(PanelRecord.current_image_url)
        .join(EpisodeRecord, EpisodeRecord.id == PanelRecord.episode_id)
        .where(
            EpisodeRecord.project_id == record.id,
            PanelRecord.current_image_url.is_not(None),
            PanelRecord.current_image_url != "",
        )
        .order_by(EpisodeRecord.position.asc(), PanelRecord.position.asc())
        .limit(1)
    )
    return str(image_url) if image_url else None


async def _project_view(session: SessionDep, record: ProjectRecord) -> Project:
    project = Project.model_validate(record)
    project.cover_image_url = await _project_cover_image_url(session, record)
    return project


@router.get("/projects", operation_id="listProjects", response_model=ProjectPage)
async def list_projects(
    request: Request,
    session: SessionDep,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: UUID | None = None,
) -> ProjectPage:
    query = (
        select(ProjectRecord)
        .where(ProjectRecord.owner_id == request.state.account_id)
        .order_by(ProjectRecord.created_at.desc(), ProjectRecord.id.desc())
        .limit(limit + 1)
    )
    if cursor is not None:
        query = query.where(ProjectRecord.id < cursor)
    rows = list((await session.scalars(query)).all())
    next_cursor = str(rows[limit - 1].id) if len(rows) > limit else None
    items = [await _project_view(session, row) for row in rows[:limit]]
    return ProjectPage(items=items, next_cursor=next_cursor)


@router.post("/projects", operation_id="createProject", response_model=Project, status_code=201)
async def create_project(body: ProjectCreate, request: Request, session: SessionDep) -> Project:
    record = ProjectRecord(**body.model_dump(), owner_id=request.state.account_id)
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return await _project_view(session, record)


@router.get(
    "/projects/{project_id}",
    operation_id="getProject",
    response_model=Project,
    dependencies=[Depends(require_project_owner_dependency)],
)
async def get_project(project_id: UUID, session: SessionDep) -> Project:
    record = await session.get(ProjectRecord, project_id)
    if record is None:
        raise _not_found("项目")
    return await _project_view(session, record)


@router.patch(
    "/projects/{project_id}",
    operation_id="updateProject",
    response_model=Project,
    dependencies=[Depends(require_project_owner_dependency)],
)
async def update_project(project_id: UUID, body: ProjectPatch, session: SessionDep) -> Project:
    record = await session.get(ProjectRecord, project_id)
    if record is None:
        raise _not_found("项目")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    record.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(record)
    return await _project_view(session, record)


@router.delete(
    "/projects/{project_id}",
    operation_id="deleteProject",
    status_code=204,
    dependencies=[Depends(require_project_owner_dependency)],
)
async def delete_project(project_id: UUID, session: SessionDep) -> Response:
    record = await session.get(ProjectRecord, project_id)
    if record is None:
        raise _not_found("项目")
    await session.delete(record)
    await session.commit()
    return Response(status_code=204)


@router.get(
    "/projects/{project_id}/episodes",
    operation_id="listEpisodes",
    response_model=list[Episode],
    dependencies=[Depends(require_project_owner_dependency)],
)
async def list_episodes(project_id: UUID, session: SessionDep) -> list[Episode]:
    if await session.get(ProjectRecord, project_id) is None:
        raise _not_found("项目")
    records = await session.scalars(
        select(EpisodeRecord)
        .where(EpisodeRecord.project_id == project_id)
        .order_by(EpisodeRecord.position)
    )
    return [Episode.model_validate(record) for record in records]


@router.post(
    "/projects/{project_id}/episodes",
    operation_id="createEpisode",
    response_model=Episode,
    status_code=201,
    dependencies=[Depends(require_project_owner_dependency)],
)
async def create_episode(project_id: UUID, body: EpisodeCreate, session: SessionDep) -> Episode:
    if await session.get(ProjectRecord, project_id) is None:
        raise _not_found("项目")
    position = await session.scalar(
        select(EpisodeRecord.position)
        .where(EpisodeRecord.project_id == project_id)
        .order_by(EpisodeRecord.position.desc())
        .limit(1)
    )
    record = EpisodeRecord(
        project_id=project_id,
        position=(position + 1 if position is not None else 0),
        **body.model_dump(),
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return Episode.model_validate(record)


@router.patch(
    "/episodes/{episode_id}",
    operation_id="updateEpisode",
    response_model=Episode,
    dependencies=[Depends(require_episode_owner)],
)
async def update_episode(episode_id: UUID, body: EpisodePatch, session: SessionDep) -> Episode:
    record = await session.get(EpisodeRecord, episode_id)
    if record is None:
        raise _not_found("故事单元")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    record.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(record)
    return Episode.model_validate(record)
