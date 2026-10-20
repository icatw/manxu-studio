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


@pytest.mark.asyncio
async def test_replace_seed_clears_shell_only_slot() -> None:
    """replace_existing must delete leftover lettering when dialogue yields no bubbles."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.schemas.workspace import EpisodeLayout, LayoutPage, PageSlot

    episode_id = uuid4()
    slot_id = uuid4()
    panel_id = uuid4()
    page_id = uuid4()
    now = datetime.now(UTC)

    page = MagicMock()
    page.id = page_id
    slot = MagicMock()
    slot.id = slot_id
    slot.panel_id = panel_id
    panel = MagicMock()
    panel.id = panel_id
    panel.dialogue = "无对白。"
    panel.character_ids = []

    existing_row = LetteringObjectRecord(
        id=uuid4(),
        slot_id=slot_id,
        kind="speech_bubble",
        text="无对白。",
        x_pct=20,
        y_pct=5,
        width_pct=36,
        tail="none",
        font_size="md",
        position=0,
        created_at=now,
        updated_at=now,
    )
    deleted: list[object] = []
    added: list[object] = []

    class FakeScalars:
        def __init__(self, rows: list[object]) -> None:
            self._rows = rows

        def all(self) -> list[object]:
            return list(self._rows)

    class FakeSession:
        async def get(self, model: object, ident: object) -> object | None:
            return None

        async def scalars(self, query: object) -> FakeScalars:
            entity = _root_entity(query)
            if entity is LetteringObjectRecord:
                # First call in lettering_for_slots / delete path — return shell row once
                return FakeScalars([existing_row] if existing_row not in deleted else [])
            return FakeScalars([])

        def add(self, obj: object) -> None:
            added.append(obj)

        async def delete(self, obj: object) -> None:
            deleted.append(obj)

        async def flush(self) -> None:
            pass

        async def commit(self) -> None:
            pass

    empty_layout = EpisodeLayout(
        episode_id=episode_id,
        template="vertical_strip",
        pages=[
            LayoutPage(
                id=page_id,
                episode_id=episode_id,
                position=0,
                template="vertical_strip",
                created_at=now,
                updated_at=now,
                slots=[
                    PageSlot(
                        id=slot_id,
                        page_id=page_id,
                        position=0,
                        panel_id=panel_id,
                        height_px=720,
                        gap_after_px=24,
                        follow_current_version=True,
                        image_version_id=None,
                        created_at=now,
                        updated_at=now,
                        lettering=[],
                    )
                ],
            )
        ],
    )

    with (
        patch(
            "app.services.lettering.layout_service.list_pages_for_episode",
            new=AsyncMock(return_value=[page]),
        ),
        patch(
            "app.services.lettering.layout_service.list_slots_for_pages",
            new=AsyncMock(return_value={page_id: [slot]}),
        ),
        patch(
            "app.services.lettering.layout_service.get_episode_layout",
            new=AsyncMock(return_value=empty_layout),
        ),
        patch(
            "app.services.lettering.lettering_for_slots",
            new=AsyncMock(
                return_value={
                    slot_id: [
                        lettering_service.lettering_view(existing_row),
                    ]
                }
            ),
        ),
    ):
        # Make session.scalars for PanelRecord return the panel
        real_scalars = FakeSession.scalars

        async def scalars_with_panels(self: FakeSession, query: object) -> FakeScalars:
            entity = _root_entity(query)
            from app.db.models import PanelRecord

            if entity is PanelRecord:
                return FakeScalars([panel])
            return await real_scalars(self, query)

        FakeSession.scalars = scalars_with_panels  # type: ignore[method-assign]

        await lettering_service.seed_lettering_from_dialogue(
            episode_id,
            SeedLetteringRequest(replace_existing=True),
            FakeSession(),  # type: ignore[arg-type]
        )

    assert existing_row in deleted or any(d is existing_row for d in deleted)
    assert added == []
