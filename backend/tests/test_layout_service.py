from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.schemas.workspace import BootstrapLayoutRequest, SlotOrder
from app.services import layout as layout_service


def _panel(episode_id, position: int):
    return SimpleNamespace(
        id=uuid4(),
        episode_id=episode_id,
        position=position,
        current_image_asset_id=None,
    )


@pytest.mark.asyncio
async def test_bootstrap_rejects_when_layout_exists() -> None:
    episode_id = uuid4()

    class FakeSession:
        async def scalars(self, query: object) -> SimpleNamespace:
            return SimpleNamespace(all=lambda: [SimpleNamespace(id=uuid4())])

    with pytest.raises(HTTPException) as exc:
        await layout_service.bootstrap_episode_layout(
            episode_id, BootstrapLayoutRequest(), FakeSession()  # type: ignore[arg-type]
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
            episode_id, None, FakeSession()  # type: ignore[arg-type]
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
