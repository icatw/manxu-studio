"""Slot-anchored lettering (LETTER A2) application service."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    CharacterRecord,
    EpisodeRecord,
    LetteringObjectRecord,
    PageSlotRecord,
    PanelRecord,
)
from app.schemas.workspace import (
    EpisodeLayout,
    LetteringObject,
    LetteringObjectCreate,
    LetteringObjectPatch,
    SeedLetteringRequest,
)
from app.services import layout as layout_service

# Exact shell words authors sometimes leave as "content" (LETTER-05).
_SHELL_TEXTS = frozenset(
    {
        "旁白",
        "对白",
        "气泡",
        "narration",
        "dialogue",
        "bubble",
        "无对白",
        "无对白。",
        "无旁白",
        "无旁白。",
    }
)

# Editor draft stubs: allowed to save, skipped when baking (LETTER-05).
_DRAFT_STUBS = frozenset({"（填写对白）", "（填写旁白）"})

# Speaker turn: "林澈：…" / "零: …" — used to split jammed multi-speaker lines (LETTER-04).
# Name chars exclude CJK/ASCII sentence punctuation and quotes so "理性评估：" mid-line
# is only reached via lookbehind after 。！？, then filtered by blocklist.
_SPEAKER_TURN = re.compile(
    r"(?:(?<=^)|(?<=[\n；;。！？!?\s]))"
    r"([^\s：:\n；;。！？!?\"“”‘’]{1,16})"
    r"[：:]"
)
# Mid-sentence labels that look like "Name：" but are not dialogue speakers.
_SPEAKER_BLOCKLIST = frozenset(
    {
        "限制",
        "注意",
        "警告",
        "说明",
        "提示",
        "系统",
        "旁白",
        "对白",
        "注",
        "例",
        "理性评估",
        "建议",
        "评估",
        "状态",
        "结论",
        "分析",
        "备注",
    }
)

SeedTail = Literal["none", "bottom_left", "bottom_right", "top_left", "top_right"]
SeedFontSize = Literal["sm", "md", "lg"]


@dataclass(frozen=True, slots=True)
class SeedBubbleGeometry:
    x_pct: float
    y_pct: float
    width_pct: float
    font_size: SeedFontSize
    tail: SeedTail


def _normalize_speaker_key(name: str) -> str:
    return "".join(name.split()).casefold()


def is_shell_lettering_text(text: str) -> bool:
    """True when text is an exact LETTER-05 shell phrase (after strip)."""
    return text.strip() in _SHELL_TEXTS


def is_draft_stub_lettering_text(text: str) -> bool:
    return text.strip() in _DRAFT_STUBS


def is_non_content_lettering_text(text: str) -> bool:
    """Shell or draft stub — skip when baking into EXP/PUBLISH pixels."""
    cleaned = text.strip()
    return not cleaned or cleaned in _SHELL_TEXTS or cleaned in _DRAFT_STUBS


def leading_speaker_name(text: str) -> str | None:
    """Return the leading「姓名：」label when present and not blocklisted."""
    match = _SPEAKER_TURN.match(text.strip())
    if match is None:
        return None
    name = match.group(1).strip()
    if not name or name in _SPEAKER_BLOCKLIST:
        return None
    return name


def strip_speaker_label(text: str) -> str:
    """Remove a leading non-blocklisted「姓名：」prefix for stored bubble body."""
    cleaned = text.strip()
    match = _SPEAKER_TURN.match(cleaned)
    if match is None:
        return cleaned
    name = match.group(1).strip()
    if not name or name in _SPEAKER_BLOCKLIST:
        return cleaned
    return cleaned[match.end() :].strip()


def seed_bubble_tail(text: str, cast_names: Sequence[str]) -> SeedTail:
    """Weak speaker→tail: first matched cast left, later right; else none."""
    speaker = leading_speaker_name(text)
    if speaker is None or not cast_names:
        return "none"
    speaker_key = _normalize_speaker_key(speaker)
    for index, name in enumerate(cast_names):
        if _normalize_speaker_key(name) == speaker_key:
            return "bottom_left" if index == 0 else "bottom_right"
    return "none"


def width_pct_for_text(text: str) -> float:
    """Flatter seed/template width heuristic (LETTER craft)."""
    length = len(text.strip())
    return max(48.0, min(84.0, 36.0 + 0.7 * length))


def default_seed_bubble_geometry(
    *,
    bubble_index: int,
    text: str,
    cast_names: Sequence[str] = (),
    bubble_count: int = 1,
    speaker_source: str | None = None,
) -> SeedBubbleGeometry:
    """Vertical-strip seed defaults.

    Single bubble: top band. Two or more: left/right dialogue geometry
    (LETTER-08 dialogue_lr). Width by length. Not vision-based avoidance.
    """
    length = len(text.strip())
    width_pct = width_pct_for_text(text)
    if length < 12:
        font_size: SeedFontSize = "lg"
    elif length > 48:
        font_size = "sm"
    else:
        font_size = "md"

    source = speaker_source if speaker_source is not None else text

    if bubble_count >= 2:
        left = bubble_index % 2 == 0
        x_pct = 8.0 if left else 48.0
        y_pct = min(70.0, 8.0 + bubble_index * 14.0)
        cast_tail = seed_bubble_tail(source, cast_names)
        if cast_tail != "none":
            tail: SeedTail = cast_tail
        else:
            tail = "bottom_left" if left else "bottom_right"
    else:
        x_pct = 20.0
        y_pct = min(68.0, 5.0 + bubble_index * 16.0)
        tail = seed_bubble_tail(source, cast_names)

    return SeedBubbleGeometry(
        x_pct=x_pct,
        y_pct=y_pct,
        width_pct=width_pct,
        font_size=font_size,
        tail=tail,
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
            detail="请填写实际对白或旁白，不能使用「旁白／对白／气泡／无对白」等占位词",
        )
    return cleaned


def _merge_speaker_only_lines(parts: list[str]) -> list[str]:
    """Merge a line that is only「Name：」with the following line (LETTER-04)."""
    merged: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        speaker = leading_speaker_name(part)
        body = strip_speaker_label(part) if speaker else part
        if speaker and not body:
            if index + 1 < len(parts):
                label = part.rstrip()
                nxt = parts[index + 1]
                if label.endswith(("：", ":")):
                    merged.append(f"{label}{nxt}")
                else:
                    merged.append(f"{label}：{nxt}")
                index += 2
                continue
            index += 1
            continue
        merged.append(part)
        index += 1
    return merged


def split_dialogue_for_bubbles(dialogue: str) -> list[str]:
    """Split panel dialogue into bubble texts (LETTER-04).

    Prefers newlines (with speaker-only line merge); otherwise splits on
    multiple Name： turns in one line. Single undivided lines stay one bubble.
    Returned chunks may still include speaker prefixes; seed strips them.
    """
    raw = dialogue.strip()
    if not raw:
        return []

    if "\n" in raw:
        parts = [part.strip() for part in raw.splitlines() if part.strip()]
        parts = _merge_speaker_only_lines(parts)
        # Trust newline structure after merge; do not re-split on Name： inside quotes.
        if parts:
            return parts

    matches = [
        match for match in _SPEAKER_TURN.finditer(raw) if match.group(1) not in _SPEAKER_BLOCKLIST
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


def prepare_seed_bubble_texts(dialogue: str) -> list[tuple[str, str]]:
    """Return (speaker_source, body) pairs ready to persist; skips shells/stubs."""
    prepared: list[tuple[str, str]] = []
    for raw in split_dialogue_for_bubbles(dialogue):
        if is_shell_lettering_text(raw) or is_draft_stub_lettering_text(raw):
            continue
        body = strip_speaker_label(raw)
        if not body or is_shell_lettering_text(body) or is_draft_stub_lettering_text(body):
            continue
        prepared.append((raw, body))
    return prepared


def lettering_view(row: LetteringObjectRecord) -> LetteringObject:
    return LetteringObject(
        id=row.id,
        slot_id=row.slot_id,
        kind=row.kind,
        text=row.text,
        x_pct=row.x_pct,
        y_pct=row.y_pct,
        width_pct=row.width_pct,
        tail=row.tail,
        font_size=row.font_size,
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
    panel_by_id = {panel.id: panel for panel in panels}
    dialogue_by_panel = {panel.id: (panel.dialogue or "").strip() for panel in panels}

    episode = await session.get(EpisodeRecord, episode_id)
    name_by_character_id: dict[str, str] = {}
    if episode is not None:
        cast_rows = list(
            (
                await session.scalars(
                    select(CharacterRecord).where(CharacterRecord.project_id == episode.project_id)
                )
            ).all()
        )
        name_by_character_id = {str(row.id): row.name for row in cast_rows}

    existing = await lettering_for_slots(session, [slot.id for slot in flat_slots])

    for slot in flat_slots:
        dialogue = dialogue_by_panel.get(slot.panel_id, "")
        prepared = prepare_seed_bubble_texts(dialogue)
        current = existing.get(slot.id, [])
        if current and not opts.replace_existing:
            continue
        # Clear first when replacing, even if dialogue is empty/shell-only
        # (otherwise「无对白。」 leftover bubbles survive a replace reseed).
        if current and opts.replace_existing:
            for item in (
                await session.scalars(
                    select(LetteringObjectRecord).where(LetteringObjectRecord.slot_id == slot.id)
                )
            ).all():
                await session.delete(item)
            await session.flush()
        if not prepared:
            continue

        panel = panel_by_id.get(slot.panel_id)
        raw_ids = panel.character_ids if panel is not None else []
        cast_names: list[str] = []
        if isinstance(raw_ids, list):
            for character_id in raw_ids:
                name = name_by_character_id.get(str(character_id))
                if name:
                    cast_names.append(name)

        bubble_count = len(prepared)
        for bubble_index, (speaker_source, bubble_text) in enumerate(prepared):
            text = validate_lettering_text(bubble_text)
            geometry = default_seed_bubble_geometry(
                bubble_index=bubble_index,
                text=text,
                cast_names=cast_names,
                bubble_count=bubble_count,
                speaker_source=speaker_source,
            )
            session.add(
                LetteringObjectRecord(
                    id=uuid4(),
                    slot_id=slot.id,
                    kind="speech_bubble",
                    text=text,
                    x_pct=geometry.x_pct,
                    y_pct=geometry.y_pct,
                    width_pct=geometry.width_pct,
                    tail=geometry.tail,
                    font_size=geometry.font_size,
                    position=bubble_index,
                )
            )

    await session.commit()
    return await layout_service.get_episode_layout(episode_id, session)
