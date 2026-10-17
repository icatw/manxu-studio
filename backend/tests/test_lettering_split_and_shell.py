"""LETTER-04 dialogue split and LETTER-05 shell-text rejection."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.db.models import LetteringObjectRecord, PageSlotRecord
from app.schemas.workspace import LetteringObjectCreate, LetteringObjectPatch
from app.services import lettering as lettering_service
from app.services.lettering import split_dialogue_for_bubbles, validate_lettering_text


def test_split_dialogue_by_newlines() -> None:
    assert split_dialogue_for_bubbles("零：你好。\n林澈：……好。") == [
        "零：你好。",
        "林澈：……好。",
    ]


def test_split_dialogue_by_speaker_turns_on_one_line() -> None:
    text = "零：宿主，可执行最优规避。限制：禁止直接干预人类自由意志。林澈：……好，我自己去。"
    parts = split_dialogue_for_bubbles(text)
    assert len(parts) == 2
    assert parts[0].startswith("零：")
    assert "限制：禁止" in parts[0]
    assert parts[1].startswith("林澈：")


def test_split_dialogue_keeps_single_line() -> None:
    assert split_dialogue_for_bubbles("只有一句，没有说话人标记。") == [
        "只有一句，没有说话人标记。"
    ]


def test_validate_rejects_shell_words() -> None:
    for shell in ("旁白", "对白", "气泡", " 旁白 "):
        with pytest.raises(HTTPException) as raised:
            validate_lettering_text(shell)
        assert raised.value.status_code == 422


def test_validate_allows_draft_stub() -> None:
    assert validate_lettering_text("（填写对白）") == "（填写对白）"
    assert validate_lettering_text("零：宿主，欢迎回来。") == "零：宿主，欢迎回来。"


@pytest.mark.asyncio
async def test_create_lettering_rejects_shell() -> None:
    slot_id = uuid4()
    now = datetime.now(UTC)
    slot = PageSlotRecord(
        id=slot_id,
        page_id=uuid4(),
        position=0,
        panel_id=uuid4(),
        image_version_id=None,
        height_px=720,
        gap_after_px=24,
        follow_current_version=True,
        created_at=now,
        updated_at=now,
    )

    class FakeSession:
        async def get(self, model: object, ident: object) -> object | None:
            return slot if ident == slot_id else None

        async def scalar(self, query: object) -> object | None:
            return None

        def add(self, obj: object) -> None:
            raise AssertionError("shell text must not be persisted")

        async def commit(self) -> None:
            pass

        async def refresh(self, obj: object) -> None:
            pass

    with pytest.raises(HTTPException) as raised:
        await lettering_service.create_lettering(
            slot_id,
            LetteringObjectCreate(kind="narration", text="旁白"),
            FakeSession(),  # type: ignore[arg-type]
        )
    assert raised.value.status_code == 422


@pytest.mark.asyncio
async def test_update_lettering_rejects_shell() -> None:
    lettering_id = uuid4()
    now = datetime.now(UTC)
    row = LetteringObjectRecord(
        id=lettering_id,
        slot_id=uuid4(),
        kind="speech_bubble",
        text="原句",
        x_pct=8,
        y_pct=6,
        width_pct=60,
        tail="bottom_left",
        font_size="md",
        position=0,
        created_at=now,
        updated_at=now,
    )

    class FakeSession:
        async def get(self, model: object, ident: object) -> object | None:
            return row if ident == lettering_id else None

        async def commit(self) -> None:
            pass

        async def refresh(self, obj: object) -> None:
            pass

    with pytest.raises(HTTPException) as raised:
        await lettering_service.update_lettering(
            lettering_id,
            LetteringObjectPatch(text="对白"),
            FakeSession(),  # type: ignore[arg-type]
        )
    assert raised.value.status_code == 422
    assert row.text == "原句"
