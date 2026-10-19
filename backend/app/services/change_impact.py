"""Compute soft change-impact summaries for cast / bible edits (IMPACT-CAST / IMPACT-BIBLE)."""

from __future__ import annotations

from collections import defaultdict
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EpisodeRecord, PanelRecord
from app.schemas.workspace import (
    ChangeImpact,
    ChangeImpactEpisode,
    CharacterPatch,
    CharacterProfile,
    ProjectPatch,
)

CAST_VISUAL_KEYS = frozenset(
    {"appearance", "hairstyle", "outfit", "signature_traits", "visual_traits", "image_prompt"}
)
BIBLE_VISUAL_KEYS = frozenset({"style_rules", "negative_prompt", "art_style", "style_seed"})
BIBLE_CONTINUITY_KEYS = frozenset({"world_setting"})

ImpactReason = Literal["cast_visual", "bible_visual", "bible_continuity"]


def cast_visual_changed_fields(
    before: CharacterProfile | dict[str, object], patch: CharacterPatch
) -> list[str]:
    if patch.profile is None:
        return []
    before_dump = (
        before.model_dump() if isinstance(before, CharacterProfile) else dict(before or {})
    )
    after = patch.profile.model_dump()
    return sorted(key for key in CAST_VISUAL_KEYS if before_dump.get(key) != after.get(key))


def bible_impact_fields(
    before: object, patch: ProjectPatch
) -> tuple[ImpactReason | None, list[str]]:
    unset = patch.model_dump(exclude_unset=True)
    visual = sorted(
        key
        for key in BIBLE_VISUAL_KEYS
        if key in unset and getattr(before, key, None) != unset[key]
    )
    continuity = sorted(
        key
        for key in BIBLE_CONTINUITY_KEYS
        if key in unset and getattr(before, key, None) != unset[key]
    )
    if visual:
        return "bible_visual", visual + continuity
    if continuity:
        return "bible_continuity", continuity
    return None, []


async def _episode_panel_counts(
    session: AsyncSession,
    *,
    project_id: UUID,
    character_id: UUID | None = None,
) -> list[ChangeImpactEpisode]:
    stmt = (
        select(
            EpisodeRecord.id,
            EpisodeRecord.position,
            EpisodeRecord.title,
            PanelRecord.character_ids,
        )
        .join(PanelRecord, PanelRecord.episode_id == EpisodeRecord.id)
        .where(
            EpisodeRecord.project_id == project_id,
            PanelRecord.current_image_asset_id.is_not(None),
        )
        .order_by(EpisodeRecord.position)
    )
    rows = (await session.execute(stmt)).all()
    per_episode: dict[UUID, ChangeImpactEpisode] = {}
    counts: dict[UUID, int] = defaultdict(int)
    target = str(character_id) if character_id is not None else None
    for episode_id, position, title, character_ids in rows:
        if target is not None:
            ids = {str(item) for item in (character_ids or [])}
            if target not in ids:
                continue
        counts[episode_id] += 1
        if episode_id not in per_episode:
            per_episode[episode_id] = ChangeImpactEpisode(
                episode_id=episode_id,
                position=position,
                title=title,
                panel_count=0,
            )
    for episode_id, summary in per_episode.items():
        summary.panel_count = counts[episode_id]
    return [summary for summary in per_episode.values() if summary.panel_count > 0]


async def impact_for_cast(
    session: AsyncSession,
    *,
    project_id: UUID,
    character_id: UUID,
    changed_fields: list[str],
) -> ChangeImpact | None:
    if not changed_fields:
        return None
    summaries = await _episode_panel_counts(
        session, project_id=project_id, character_id=character_id
    )
    return ChangeImpact(
        reason="cast_visual",
        changed_fields=changed_fields,
        affected_panel_count=sum(item.panel_count for item in summaries),
        affected_episode_ids=[item.episode_id for item in summaries],
        affected_episode_summaries=summaries,
    )


async def impact_for_bible(
    session: AsyncSession,
    *,
    project_id: UUID,
    reason: ImpactReason,
    changed_fields: list[str],
) -> ChangeImpact:
    if reason == "bible_continuity":
        return ChangeImpact(
            reason=reason,
            changed_fields=changed_fields,
            affected_panel_count=0,
            affected_episode_ids=[],
            affected_episode_summaries=[],
        )
    summaries = await _episode_panel_counts(session, project_id=project_id)
    return ChangeImpact(
        reason=reason,
        changed_fields=changed_fields,
        affected_panel_count=sum(item.panel_count for item in summaries),
        affected_episode_ids=[item.episode_id for item in summaries],
        affected_episode_summaries=summaries,
    )
