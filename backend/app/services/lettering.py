"""Slot-anchored lettering (LETTER A2) application service."""

from __future__ import annotations

import re
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import LetteringObjectRecord, PageSlotRecord, PanelRecord
from app.schemas.workspace import (
    EpisodeLayout,
    LetteringObject,
    LetteringObjectCreate,
    LetteringObjectPatch,
    SeedLetteringRequest,
)
from app.services import layout as layout_service

# Exact shell words authors sometimes leave as "content" (LETTER-05).
_SHELL_TEXTS = frozenset({"旁白", "对白", "气泡", "narration", "dialogue", "bubble"})

# Speaker turn: "林澈：…" / "零: …" — used to split jammed multi-speaker lines (LETTER-04).
_SPEAKER_TURN = re.compile(
    r"(?:(?<=^)|(?<=[\n；;。！？!?\s]))"
    r"([^\s：:\n]{1,16})"
    r"[：:]"
)
# Mid-sentence labels that look like "Name：" but are not dialogue speakers.
_SPEAKER_BLOCKLIST = frozenset(
    {"限制", "注意", "警告", "说明", "提示", "系统", "旁白", "对白", "注", "例"}
)


def _not_found(resource: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{resource}不存在")


def validate_lettering_text(text: str) -> str:
    """Normalize and reject empty / shell-only lettering bodies (LETTER-05)."""
    cleaned = text.strip()
    if not cleaned:
        raise HTTPException(status_code=422, detail="字效文案不能为空")
    if cleaned in _SHELL_TEXTS:
        raise HTTPException(
            status_code=422,
            detail="请填写实际对白或旁白，不能使用「旁白／对白／气泡」等占位词",
        )
    return cleaned


def split_dialogue_for_bubbles(dialogue: str) -> list[str]:
    """Split panel dialogue into bubble texts (LETTER-04).

    Prefers newlines; otherwise splits on multiple Name： turns in one line.
    Single undivided lines stay one bubble.
    """
    raw = dialogue.strip()
    if not raw:
        return []

    if "\n" in raw:
        parts = [part.strip() for part in raw.splitlines() if part.strip()]
        if len(parts) > 1:
            return parts

    matches = [
        match
        for match in _SPEAKER_TURN.finditer(raw)
        if match.group(1) not in _SPEAKER_BLOCKLIST
    ]
    if len(matches) >= 2:
        chunks: list[str] = []
        for index, match in enumerate(matches):
            start = match.start()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(raw)
            chunk = raw[start:end].strip().strip("；;")
            if chunk:
                chunks.append(chunk)
        if len(chunks) >= 2:
            return chunks

    return [raw]


def lettering_view(row: LetteringObjectRecord) -> LetteringObject:
    return LetteringObject(
        id=row.id,
        slot_id=row.slot_id,
        kind=row.kind,  # type: ignore[arg-type]
        text=row.text,
        x_pct=row.x_pct,
        y_pct=row.y_pct,
        width_pct=row.width_pct,
        tail=row.tail,  # type: ignore[arg-type]
        font_size=row.font_size,  # type: ignore[arg-type]
        position=row.position,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def lettering_for_slots(
    session: AsyncSession, slot_ids: list[UUID]
) -> dict[UUID, list[LetteringObject]]:
    if not slot_ids:
        return {}
    result = await session.scalars(
        select(LetteringObjectRecord)
        .where(LetteringObjectRecord.slot_id.in_(slot_ids))
        .order_by(LetteringObjectRecord.slot_id, LetteringObjectRecord.position)
    )
    grouped: dict[UUID, list[LetteringObject]] = {slot_id: [] for slot_id in slot_ids}
    for row in result.all():
        grouped.setdefault(row.slot_id, []).append(lettering_view(row))
    return grouped


async def _next_position(session: AsyncSession, slot_id: UUID) -> int:
    current = await session.scalar(
        select(LetteringObjectRecord.position)
        .where(LetteringObjectRecord.slot_id == slot_id)
        .order_by(LetteringObjectRecord.position.desc())
        .limit(1)
    )
    return 0 if current is None else int(current) + 1


async def create_lettering(
    slot_id: UUID,
    body: LetteringObjectCreate,
    session: AsyncSession,
) -> LetteringObject:
    slot = await session.get(PageSlotRecord, slot_id)
    if slot is None:
        raise _not_found("槽位")
    text = validate_lettering_text(body.text)
    row = LetteringObjectRecord(
        id=uuid4(),
        slot_id=slot_id,
        kind=body.kind,
        text=text,
        x_pct=body.x_pct,
        y_pct=body.y_pct,
        width_pct=body.width_pct,
        tail=body.tail,
        font_size=body.font_size,
        position=await _next_position(session, slot_id),
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return lettering_view(row)


async def update_lettering(
    lettering_id: UUID,
    body: LetteringObjectPatch,
    session: AsyncSession,
) -> LetteringObject:
    row = await session.get(LetteringObjectRecord, lettering_id)
    if row is None:
        raise _not_found("字效")
    if body.kind is not None:
        row.kind = body.kind
    if body.text is not None:
        row.text = validate_lettering_text(body.text)
    if body.x_pct is not None:
        row.x_pct = body.x_pct
    if body.y_pct is not None:
        row.y_pct = body.y_pct
    if body.width_pct is not None:
        row.width_pct = body.width_pct
    if body.tail is not None:
        row.tail = body.tail
    if body.font_size is not None:
        row.font_size = body.font_size
    if body.position is not None:
        row.position = body.position
    await session.commit()
    await session.refresh(row)
    return lettering_view(row)


async def delete_lettering(lettering_id: UUID, session: AsyncSession) -> None:
    row = await session.get(LetteringObjectRecord, lettering_id)
    if row is None:
        raise _not_found("字效")
    await session.delete(row)
    await session.commit()


async def seed_lettering_from_dialogue(
    episode_id: UUID,
    body: SeedLetteringRequest | None,
    session: AsyncSession,
) -> EpisodeLayout:
    opts = body or SeedLetteringRequest()
    pages = await layout_service.list_pages_for_episode(session, episode_id)
    if not pages:
        raise _not_found("成稿布局")

    slots_by_page = await layout_service.list_slots_for_pages(session, [page.id for page in pages])
    flat_slots = [slot for page in pages for slot in slots_by_page.get(page.id, [])]
    if not flat_slots:
        return await layout_service.get_episode_layout(episode_id, session)

    panel_ids = [slot.panel_id for slot in flat_slots]
    panels = list(
        (await session.scalars(select(PanelRecord).where(PanelRecord.id.in_(panel_ids)))).all()
    )
    dialogue_by_panel = {panel.id: (panel.dialogue or "").strip() for panel in panels}

    existing = await lettering_for_slots(session, [slot.id for slot in flat_slots])

    for index, slot in enumerate(flat_slots):
        dialogue = dialogue_by_panel.get(slot.panel_id, "")
        bubbles = split_dialogue_for_bubbles(dialogue)
        if not bubbles:
            continue
        current = existing.get(slot.id, [])
        if current and not opts.replace_existing:
            continue
        if current and opts.replace_existing:
            for item in (
                await session.scalars(
                    select(LetteringObjectRecord).where(LetteringObjectRecord.slot_id == slot.id)
                )
            ).all():
                await session.delete(item)
            await session.flush()

        even = index % 2 == 0
        for bubble_index, bubble_text in enumerate(bubbles):
            text = validate_lettering_text(bubble_text)
            y_pct = min(70.0, 6.0 + bubble_index * 18.0)
            session.add(
                LetteringObjectRecord(
                    id=uuid4(),
                    slot_id=slot.id,
                    kind="speech_bubble",
                    text=text,
                    x_pct=8.0 if even else 32.0,
                    y_pct=y_pct,
                    width_pct=60.0,
                    tail="bottom_left" if even else "bottom_right",
                    font_size="md",
                    position=bubble_index,
                )
            )

    await session.commit()
    return await layout_service.get_episode_layout(episode_id, session)
