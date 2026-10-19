"""Project and episode application service."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EpisodeRecord, PanelRecord, ProjectRecord
from app.schemas.workspace import (
    Episode,
    EpisodeCreate,
    EpisodePatch,
    Project,
    ProjectCreate,
    ProjectPage,
    ProjectPatch,
    ProjectUpdateResult,
)
from app.services.change_impact import bible_impact_fields, impact_for_bible
from app.services.planned_outline import resolve_episode_seed


def not_found(resource: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{resource}不存在")


async def project_cover_image_url(session: AsyncSession, record: ProjectRecord) -> str | None:
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


async def project_view(session: AsyncSession, record: ProjectRecord) -> Project:
    project = Project.model_validate(record)
    project.cover_image_url = await project_cover_image_url(session, record)
    return project


async def list_projects(
    session: AsyncSession, *, owner_id: UUID, limit: int, cursor: UUID | None
) -> ProjectPage:
    query = (
        select(ProjectRecord)
        .where(ProjectRecord.owner_id == owner_id)
        .order_by(ProjectRecord.created_at.desc(), ProjectRecord.id.desc())
        .limit(limit + 1)
    )
    if cursor is not None:
        query = query.where(ProjectRecord.id < cursor)
    rows = list((await session.scalars(query)).all())
    next_cursor = str(rows[limit - 1].id) if len(rows) > limit else None
    items = [await project_view(session, row) for row in rows[:limit]]
    return ProjectPage(items=items, next_cursor=next_cursor)


async def create_project(session: AsyncSession, *, owner_id: UUID, body: ProjectCreate) -> Project:
    record = ProjectRecord(**body.model_dump(), owner_id=owner_id)
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return await project_view(session, record)


async def get_project(session: AsyncSession, project_id: UUID) -> Project:
    record = await session.get(ProjectRecord, project_id)
    if record is None:
        raise not_found("项目")
    return await project_view(session, record)


async def update_project(
    session: AsyncSession, project_id: UUID, body: ProjectPatch
) -> ProjectUpdateResult:
    record = await session.get(ProjectRecord, project_id)
    if record is None:
        raise not_found("项目")
    reason, changed_fields = bible_impact_fields(record, body)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    record.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(record)
    project = await project_view(session, record)
    impact = None
    if reason is not None:
        impact = await impact_for_bible(
            session,
            project_id=project_id,
            reason=reason,
            changed_fields=changed_fields,
        )
    return ProjectUpdateResult(project=project, impact=impact)


async def delete_project(session: AsyncSession, project_id: UUID) -> None:
    record = await session.get(ProjectRecord, project_id)
    if record is None:
        raise not_found("项目")
    await session.delete(record)
    await session.commit()


async def list_episodes(session: AsyncSession, project_id: UUID) -> list[Episode]:
    if await session.get(ProjectRecord, project_id) is None:
        raise not_found("项目")
    records = await session.scalars(
        select(EpisodeRecord)
        .where(EpisodeRecord.project_id == project_id)
        .order_by(EpisodeRecord.position)
    )
    return [Episode.model_validate(record) for record in records]


async def create_episode(session: AsyncSession, project_id: UUID, body: EpisodeCreate) -> Episode:
    project = await session.get(ProjectRecord, project_id)
    if project is None:
        raise not_found("项目")
    position = await session.scalar(
        select(EpisodeRecord.position)
        .where(EpisodeRecord.project_id == project_id)
        .order_by(EpisodeRecord.position.desc())
        .limit(1)
    )
    next_position = position + 1 if position is not None else 0
    episode_number = next_position + 1
    title, synopsis = resolve_episode_seed(
        episode_number=episode_number,
        title=body.title,
        synopsis=body.synopsis,
        project_synopsis=project.synopsis,
        world_setting=project.world_setting,
    )
    payload = body.model_dump()
    payload["title"] = title
    payload["synopsis"] = synopsis
    record = EpisodeRecord(
        project_id=project_id,
        position=next_position,
        **payload,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return Episode.model_validate(record)


async def update_episode(session: AsyncSession, episode_id: UUID, body: EpisodePatch) -> Episode:
    record = await session.get(EpisodeRecord, episode_id)
    if record is None:
        raise not_found("故事单元")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    record.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(record)
    return Episode.model_validate(record)
