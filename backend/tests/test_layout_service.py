from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.db.models import LayoutPageRecord, LetteringObjectRecord, PageSlotRecord, PanelRecord
from app.schemas.workspace import BootstrapLayoutRequest, SlotOrder, SyncLayoutRequest
from app.services import layout as layout_service


def _panel(episode_id, position: int):
    return SimpleNamespace(
        id=uuid4(),
        episode_id=episode_id,
        position=position,
        current_image_asset_id=None,
    )


def _root_entity(query: object) -> type | None:
    try:
        descriptions = query.column_descriptions  # type: ignore[attr-defined]
    except AttributeError:
        return None
    if not descriptions:
        return None
    return descriptions[0].get("entity")


@pytest.mark.asyncio
async def test_bootstrap_rejects_when_layout_exists() -> None:
    episode_id = uuid4()

    class FakeSession:
        async def scalars(self, query: object) -> SimpleNamespace:
            return SimpleNamespace(all=lambda: [SimpleNamespace(id=uuid4())])

    with pytest.raises(HTTPException) as exc:
        await layout_service.bootstrap_episode_layout(
            episode_id,
            BootstrapLayoutRequest(),
            FakeSession(),  # type: ignore[arg-type]
        )
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_bootstrap_rejects_empty_panels() -> None:
    episode_id = uuid4()
    calls = {"n": 0}

    class FakeSession:
        async def scalars(self, query: object) -> SimpleNamespace:
            calls["n"] += 1
            # first call: existing pages; second: panels
            if calls["n"] == 1:
                return SimpleNamespace(all=lambda: [])
            return SimpleNamespace(all=lambda: [])

    with pytest.raises(HTTPException) as exc:
        await layout_service.bootstrap_episode_layout(
            episode_id,
            None,
            FakeSession(),  # type: ignore[arg-type]
        )
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_reorder_page_slots() -> None:
    page_id = uuid4()
    episode_id = uuid4()
    slot_a = SimpleNamespace(
        id=uuid4(),
        page_id=page_id,
        position=0,
        panel_id=uuid4(),
        image_version_id=None,
        height_px=720,
        gap_after_px=24,
        follow_current_version=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    slot_b = SimpleNamespace(
        id=uuid4(),
        page_id=page_id,
        position=1,
        panel_id=uuid4(),
        image_version_id=None,
        height_px=720,
        gap_after_px=24,
        follow_current_version=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    page = SimpleNamespace(
        id=page_id,
        episode_id=episode_id,
        position=0,
        template="vertical_strip",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    calls = {"scalars": 0}

    class FakeSession:
        async def get(self, model: object, ident: object) -> object | None:
            if ident == page_id:
                return page
            return None

        async def scalars(self, query: object) -> SimpleNamespace:
            entity = _root_entity(query)
            if entity is LetteringObjectRecord:
                return SimpleNamespace(all=lambda: [])
            calls["scalars"] += 1
            # reorder loads slots; then _layout_view loads pages then slots
            if calls["scalars"] == 1:
                return SimpleNamespace(all=lambda: [slot_a, slot_b])
            if calls["scalars"] == 2:
                return SimpleNamespace(all=lambda: [page])
            return SimpleNamespace(all=lambda: [slot_b, slot_a])

        async def commit(self) -> None:
            pass

    body = SlotOrder(slot_ids=[slot_b.id, slot_a.id])
    result = await layout_service.reorder_page_slots(page_id, body, FakeSession())  # type: ignore[arg-type]
    assert [s.id for s in result.slots] == [slot_b.id, slot_a.id]
    assert slot_b.position == 0
    assert slot_a.position == 1


def _stamp_timestamps(obj: object) -> None:
    now = datetime.now(UTC)
    if getattr(obj, "created_at", None) is None:
        obj.created_at = now  # type: ignore[attr-defined]
    if getattr(obj, "updated_at", None) is None:
        obj.updated_at = now  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_bootstrap_creates_one_slot_per_panel() -> None:
    episode_id = uuid4()
    panels = [_panel(episode_id, 0), _panel(episode_id, 1)]
    pages: list[object] = []
    slots: list[object] = []

    class FakeSession:
        def add(self, obj: object) -> None:
            _stamp_timestamps(obj)
            if isinstance(obj, LayoutPageRecord):
                pages.append(obj)
            elif isinstance(obj, PageSlotRecord):
                slots.append(obj)

        async def flush(self) -> None:
            pass

        async def commit(self) -> None:
            pass

        async def scalar(self, query: object) -> object | None:
            return None

        async def scalars(self, query: object) -> SimpleNamespace:
            entity = _root_entity(query)
            if entity is LayoutPageRecord:
                return SimpleNamespace(all=lambda: list(pages))
            if entity is PanelRecord:
                return SimpleNamespace(all=lambda: list(panels))
            if entity is PageSlotRecord:
                return SimpleNamespace(all=lambda: list(slots))
            if entity is LetteringObjectRecord:
                return SimpleNamespace(all=lambda: [])
            return SimpleNamespace(all=lambda: [])

    result = await layout_service.bootstrap_episode_layout(
        episode_id,
        BootstrapLayoutRequest(default_height_px=640, default_gap_px=16),
        FakeSession(),  # type: ignore[arg-type]
    )
    assert len(result.pages) == 1
    assert len(result.pages[0].slots) == 2
    assert [slot.panel_id for slot in result.pages[0].slots] == [panels[0].id, panels[1].id]
    assert all(slot.height_px == 640 for slot in result.pages[0].slots)
    assert all(slot.gap_after_px == 16 for slot in result.pages[0].slots)


@pytest.mark.asyncio
async def test_sync_appends_new_panels_and_drops_deleted() -> None:
    episode_id = uuid4()
    page_id = uuid4()
    kept = _panel(episode_id, 0)
    removed = _panel(episode_id, 1)
    added = _panel(episode_id, 2)
    now = datetime.now(UTC)
    page = LayoutPageRecord(
        id=page_id,
        episode_id=episode_id,
        position=0,
        template="vertical_strip",
        created_at=now,
        updated_at=now,
    )
    slot_kept = PageSlotRecord(
        id=uuid4(),
        page_id=page_id,
        position=0,
        panel_id=kept.id,
        image_version_id=None,
        height_px=720,
        gap_after_px=24,
        follow_current_version=True,
        created_at=now,
        updated_at=now,
    )
    slot_removed = PageSlotRecord(
        id=uuid4(),
        page_id=page_id,
        position=1,
        panel_id=removed.id,
        image_version_id=None,
        height_px=720,
        gap_after_px=24,
        follow_current_version=True,
        created_at=now,
        updated_at=now,
    )
    pages = [page]
    slots = [slot_kept, slot_removed]
    panels = [kept, added]
    deleted: list[object] = []

    class FakeSession:
        def add(self, obj: object) -> None:
            _stamp_timestamps(obj)
            if isinstance(obj, PageSlotRecord):
                slots.append(obj)

        async def delete(self, obj: object) -> None:
            deleted.append(obj)
            if obj in slots:
                slots.remove(obj)

        async def flush(self) -> None:
            pass

        async def commit(self) -> None:
            pass

        async def scalar(self, query: object) -> object | None:
            return None

        async def scalars(self, query: object) -> SimpleNamespace:
            entity = _root_entity(query)
            if entity is LayoutPageRecord:
                return SimpleNamespace(all=lambda: list(pages))
            if entity is PanelRecord:
                return SimpleNamespace(all=lambda: list(panels))
            if entity is PageSlotRecord:
                return SimpleNamespace(all=lambda: list(slots))
            if entity is LetteringObjectRecord:
                return SimpleNamespace(all=lambda: [])
            return SimpleNamespace(all=lambda: [])

    result = await layout_service.sync_episode_layout(
        episode_id,
        SyncLayoutRequest(follow_current_version=True),
        FakeSession(),  # type: ignore[arg-type]
    )
    assert slot_removed in deleted
    panel_ids = [slot.panel_id for slot in result.pages[0].slots]
    assert kept.id in panel_ids
    assert added.id in panel_ids
    assert removed.id not in panel_ids
