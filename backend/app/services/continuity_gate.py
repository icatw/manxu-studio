"""SERIAL-03: previous episode must have a summary before generating the next."""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EpisodeRecord


async def require_previous_episode_summary(session: AsyncSession, episode: EpisodeRecord) -> None:
    previous = await session.scalar(
        select(EpisodeRecord)
        .where(
            EpisodeRecord.project_id == episode.project_id,
            EpisodeRecord.position < episode.position,
        )
        .order_by(EpisodeRecord.position.desc())
        .limit(1)
    )
    if previous is None:
        return
    if previous.summary.strip():
        return
    raise HTTPException(
        status_code=409,
        detail=f"请先为「{previous.title}」生成摘要，再生成下一话分镜",
    )


async def previous_episode_missing_summary(
    session: AsyncSession, *, project_id: UUID, episode_id: UUID
) -> EpisodeRecord | None:
    episode = await session.get(EpisodeRecord, episode_id)
    if episode is None or episode.project_id != project_id:
        return None
    previous = await session.scalar(
        select(EpisodeRecord)
        .where(
            EpisodeRecord.project_id == episode.project_id,
            EpisodeRecord.position < episode.position,
        )
        .order_by(EpisodeRecord.position.desc())
        .limit(1)
    )
    if previous is None or previous.summary.strip():
        return None
    return previous
