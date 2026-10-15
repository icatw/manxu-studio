from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.schemas.workspace import PanelOrder
from app.services import storyboard as storyboard_service


@pytest.mark.asyncio
async def test_reorder_panels_refreshes_after_commit() -> None:
    episode_id = uuid4()
    panel_a = SimpleNamespace(
        id=uuid4(),
        episode_id=episode_id,
        position=0,
        scene_description="",
        shot="中景",
        composition="",
        character_actions="",
        emotion="",
        dialogue="",
        story_purpose="",
        image_prompt="",
        character_ids=[],
        scene_id=None,
        review_status="draft",
        current_image_asset_id=None,
        version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    panel_b = SimpleNamespace(
        id=uuid4(),
        episode_id=episode_id,
        position=1,
        scene_description="",
        shot="近景",
        composition="",
        character_actions="",
        emotion="",
        dialogue="",
        story_purpose="",
        image_prompt="",
        character_ids=[],
        scene_id=None,
        review_status="draft",
        current_image_asset_id=None,
        version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    rows = [panel_a, panel_b]
    refreshed: list[object] = []

    class FakeSession:
        async def scalars(self, query: object) -> SimpleNamespace:
            return SimpleNamespace(all=lambda: rows)

        async def flush(self) -> None:
            pass

        async def commit(self) -> None:
            # Simulate expire_on_commit: accessing attrs after commit would fail without refresh.
            for row in rows:
                row.updated_at = None

        async def refresh(self, row: object) -> None:
            refreshed.append(row)
            row.updated_at = datetime.now(UTC)  # type: ignore[attr-defined]

    body = PanelOrder(panel_ids=[panel_b.id, panel_a.id])
    result = await storyboard_service.reorder_panels(episode_id, body, FakeSession())  # type: ignore[arg-type]

    assert [item.id for item in result] == [panel_b.id, panel_a.id]
    assert panel_b.position == 0
    assert panel_a.position == 1
    assert refreshed == [panel_b, panel_a]
