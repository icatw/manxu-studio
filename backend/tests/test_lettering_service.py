from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.db.models import LetteringObjectRecord, PageSlotRecord
from app.schemas.workspace import LetteringObjectCreate, SeedLetteringRequest
from app.services import lettering as lettering_service


def _root_entity(query: object) -> type | None:
    try:
        descriptions = query.column_descriptions  # type: ignore[attr-defined]
    except AttributeError:
        return None
    if not descriptions:
        return None
    return descriptions[0].get("entity")


@pytest.mark.asyncio
async def test_seed_requires_layout() -> None:
    class FakeSession:
        async def scalars(self, query: object) -> SimpleNamespace:
            return SimpleNamespace(all=lambda: [])

    with pytest.raises(HTTPException) as exc:
        await lettering_service.seed_lettering_from_dialogue(
            uuid4(),
            SeedLetteringRequest(),
            FakeSession(),  # type: ignore[arg-type]
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_create_lettering_appends_position() -> None:
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
    added: list[LetteringObjectRecord] = []

    class FakeSession:
        async def get(self, model: object, ident: object) -> object | None:
            if ident == slot_id:
                return slot
            return None

        async def scalar(self, query: object) -> object | None:
            return 0 if added else None

        def add(self, obj: object) -> None:
            if isinstance(obj, LetteringObjectRecord):
                if obj.created_at is None:
                    obj.created_at = now
                if obj.updated_at is None:
                    obj.updated_at = now
                added.append(obj)

        async def commit(self) -> None:
            pass

        async def refresh(self, obj: object) -> None:
            pass

    result = await lettering_service.create_lettering(
        slot_id,
        LetteringObjectCreate(kind="speech_bubble", text="你好"),
        FakeSession(),  # type: ignore[arg-type]
    )
    assert result.text == "你好"
    assert result.position == 0
    assert len(added) == 1
