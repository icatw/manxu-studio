"""SERIAL-03 continue-next frontier (server mirror of frontend episode-frontier)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EpisodeRecord


@dataclass(frozen=True)
class FrontierStay:
    kind: str  # stay | studio
    episode_id: UUID
    message: str


@dataclass(frozen=True)
class FrontierCreateNext:
    kind: str = "create_next"


async def list_project_episodes_ordered(
    session: AsyncSession, project_id: UUID
) -> list[EpisodeRecord]:
    rows = await session.scalars(
        select(EpisodeRecord)
        .where(EpisodeRecord.project_id == project_id)
        .order_by(EpisodeRecord.position)
    )
    return list(rows.all())


def resolve_continue_next(
    episodes: list[EpisodeRecord],
) -> FrontierStay | FrontierCreateNext:
    frontier_idx = next(
        (index for index, episode in enumerate(episodes) if not (episode.summary or "").strip()),
        None,
    )
    if frontier_idx == 0:
        first = episodes[0]
        return FrontierStay(
            kind="stay",
            episode_id=first.id,
            message=f"请先为「{first.title}」生成摘要，再续写下一话",
        )
    if frontier_idx is not None and frontier_idx > 0:
        target = episodes[frontier_idx]
        return FrontierStay(
            kind="studio",
            episode_id=target.id,
            message=f"已打开「{target.title}」；该话尚无摘要，可先出分镜或稍后补摘要",
        )
    return FrontierCreateNext()
