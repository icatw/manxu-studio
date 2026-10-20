"""Multi-episode manuscript strip preview (COLLECT-PREVIEW-01)."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EpisodeRecord, LayoutPageRecord, PageSlotRecord, ProjectRecord
from app.schemas.workspace import AnthologyPreview, AnthologyPreviewChapter
from app.services import layout as layout_service


def _not_found(resource: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{resource}不存在")


async def get_project_anthology_preview(
    session: AsyncSession,
    *,
    project_id: UUID,
    episode_ids: list[UUID],
) -> AnthologyPreview:
    if not episode_ids:
        raise HTTPException(status_code=422, detail="请至少选择一话")
    if len(episode_ids) > 40:
        raise HTTPException(status_code=422, detail="合集预览最多选择 40 话")
    if len(set(episode_ids)) != len(episode_ids):
        raise HTTPException(status_code=422, detail="话次列表不能重复")

    project = await session.get(ProjectRecord, project_id)
    if project is None:
        raise _not_found("项目")

    episodes = list(
        (
            await session.scalars(
                select(EpisodeRecord).where(
                    EpisodeRecord.project_id == project_id,
                    EpisodeRecord.id.in_(episode_ids),
                )
            )
        ).all()
    )
    by_id = {episode.id: episode for episode in episodes}
    missing = [episode_id for episode_id in episode_ids if episode_id not in by_id]
    if missing:
        raise HTTPException(status_code=422, detail="合集预览包含无效或不属于本作品的话次")

    chapters: list[AnthologyPreviewChapter] = []
    for episode_id in episode_ids:
        episode = by_id[episode_id]
        page_ids = list(
            (
                await session.scalars(
                    select(LayoutPageRecord.id).where(LayoutPageRecord.episode_id == episode_id)
                )
            ).all()
        )
        if not page_ids:
            chapters.append(
                AnthologyPreviewChapter(
                    episode_id=episode.id,
                    position=episode.position,
                    title=episode.title,
                    ready=False,
                    skip_reason="no_layout",
                    preview=None,
                )
            )
            continue

        slot_count = await session.scalar(
            select(PageSlotRecord.id).where(PageSlotRecord.page_id.in_(page_ids)).limit(1)
        )
        if slot_count is None:
            chapters.append(
                AnthologyPreviewChapter(
                    episode_id=episode.id,
                    position=episode.position,
                    title=episode.title,
                    ready=False,
                    skip_reason="empty_slots",
                    preview=None,
                )
            )
            continue

        preview = await layout_service.get_episode_layout_preview(episode_id, session)
        chapters.append(
            AnthologyPreviewChapter(
                episode_id=episode.id,
                position=episode.position,
                title=episode.title,
                ready=True,
                skip_reason=None,
                preview=preview,
            )
        )

    return AnthologyPreview(project_id=project_id, chapters=chapters)
