"""Anthology manuscript strip preview (COLLECT-PREVIEW-01)."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.redis import require_rate_limit
from app.core.security import current_account_dependency
from app.db.models import EpisodeRecord, LayoutPageRecord, ProjectRecord
from app.db.session import get_session
from app.main import app
from app.schemas.workspace import LayoutPreview, LayoutPreviewItem, LetteringObject
from app.services import anthology as anthology_service


def _root_entity(query: object) -> type | None:
    try:
        descriptions = query.column_descriptions  # type: ignore[attr-defined]
    except AttributeError:
        return None
    if not descriptions:
        return None
    return descriptions[0].get("entity")


@pytest.mark.asyncio
async def test_ready_and_unready_chapters_mixed() -> None:
    project_id = uuid4()
    ready_id = uuid4()
    no_layout_id = uuid4()
    empty_slots_id = uuid4()
    page_id = uuid4()
    empty_page_id = uuid4()
    slot_id = uuid4()
    now = datetime.now(UTC)
    lettering = LetteringObject(
        id=uuid4(),
        slot_id=slot_id,
        kind="speech_bubble",
        text="你好",
        x_pct=20,
        y_pct=30,
        width_pct=40,
        tail="bottom_left",
        font_size="md",
        position=0,
        created_at=now,
        updated_at=now,
    )
    preview = LayoutPreview(
        episode_id=ready_id,
        items=[
            LayoutPreviewItem(
                slot_id=slot_id,
                page_id=page_id,
                panel_id=uuid4(),
                height_px=720,
                gap_after_px=24,
                image_url="https://example.com/panel.png",
                lettering=[lettering],
            )
        ],
    )

    # Per-episode page lookup order matches episode_ids request order.
    page_lookup_queue: list[list[object]] = [
        [page_id],  # ready
        [],  # no_layout
        [empty_page_id],  # empty_slots
    ]
    slot_lookup_queue: list[object | None] = [slot_id, None]

    class PreciseSession:
        async def get(self, model: type[object], record_id: object) -> object | None:
            if model is ProjectRecord and record_id == project_id:
                return SimpleNamespace(id=project_id)
            return None

        async def scalars(self, query: object) -> SimpleNamespace:
            entity = _root_entity(query)
            if entity is EpisodeRecord:
                return SimpleNamespace(
                    all=lambda: [
                        SimpleNamespace(
                            id=ready_id, position=0, title="第一话", project_id=project_id
                        ),
                        SimpleNamespace(
                            id=no_layout_id, position=1, title="第二话", project_id=project_id
                        ),
                        SimpleNamespace(
                            id=empty_slots_id, position=2, title="第三话", project_id=project_id
                        ),
                    ]
                )
            if entity is LayoutPageRecord:
                return SimpleNamespace(all=lambda: page_lookup_queue.pop(0))
            return SimpleNamespace(all=lambda: [])

        async def scalar(self, query: object) -> object | None:
            return slot_lookup_queue.pop(0)

    with patch.object(
        anthology_service.layout_service,
        "get_episode_layout_preview",
        new=AsyncMock(return_value=preview),
    ):
        result = await anthology_service.get_project_anthology_preview(
            PreciseSession(),  # type: ignore[arg-type]
            project_id=project_id,
            episode_ids=[ready_id, no_layout_id, empty_slots_id],
        )

    assert result.kind == "anthology_preview"
    assert result.project_id == project_id
    assert len(result.chapters) == 3
    assert result.chapters[0].ready is True
    assert result.chapters[0].skip_reason is None
    assert result.chapters[0].preview is not None
    assert result.chapters[0].preview.items[0].lettering[0].text == "你好"
    assert result.chapters[1].ready is False
    assert result.chapters[1].skip_reason == "no_layout"
    assert result.chapters[1].preview is None
    assert result.chapters[2].ready is False
    assert result.chapters[2].skip_reason == "empty_slots"


@pytest.mark.asyncio
async def test_invalid_episode_id_returns_422() -> None:
    project_id = uuid4()
    valid_id = uuid4()
    foreign_id = uuid4()

    class FakeSession:
        async def get(self, model: type[object], record_id: object) -> object | None:
            if model is ProjectRecord and record_id == project_id:
                return SimpleNamespace(id=project_id)
            return None

        async def scalars(self, query: object) -> SimpleNamespace:
            return SimpleNamespace(
                all=lambda: [
                    SimpleNamespace(id=valid_id, position=0, title="第一话", project_id=project_id)
                ]
            )

    with pytest.raises(HTTPException) as exc:
        await anthology_service.get_project_anthology_preview(
            FakeSession(),  # type: ignore[arg-type]
            project_id=project_id,
            episode_ids=[valid_id, foreign_id],
        )
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_missing_project_returns_404() -> None:
    class FakeSession:
        async def get(self, model: type[object], record_id: object) -> object | None:
            return None

    with pytest.raises(HTTPException) as exc:
        await anthology_service.get_project_anthology_preview(
            FakeSession(),  # type: ignore[arg-type]
            project_id=uuid4(),
            episode_ids=[uuid4()],
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_duplicate_and_empty_lists_rejected() -> None:
    project_id = uuid4()
    episode_id = uuid4()

    class FakeSession:
        async def get(self, model: type[object], record_id: object) -> object | None:
            return SimpleNamespace(id=project_id)

    with pytest.raises(HTTPException) as exc_empty:
        await anthology_service.get_project_anthology_preview(
            FakeSession(),  # type: ignore[arg-type]
            project_id=project_id,
            episode_ids=[],
        )
    assert exc_empty.value.status_code == 422

    with pytest.raises(HTTPException) as exc_dup:
        await anthology_service.get_project_anthology_preview(
            FakeSession(),  # type: ignore[arg-type]
            project_id=project_id,
            episode_ids=[episode_id, episode_id],
        )
    assert exc_dup.value.status_code == 422


@pytest.mark.asyncio
async def test_preserves_request_order() -> None:
    project_id = uuid4()
    first = uuid4()
    second = uuid4()

    class FakeSession:
        async def get(self, model: type[object], record_id: object) -> object | None:
            return SimpleNamespace(id=project_id)

        async def scalars(self, query: object) -> SimpleNamespace:
            entity = _root_entity(query)
            if entity is EpisodeRecord:
                return SimpleNamespace(
                    all=lambda: [
                        SimpleNamespace(id=second, position=1, title="后", project_id=project_id),
                        SimpleNamespace(id=first, position=0, title="前", project_id=project_id),
                    ]
                )
            return SimpleNamespace(all=lambda: [])

    result = await anthology_service.get_project_anthology_preview(
        FakeSession(),  # type: ignore[arg-type]
        project_id=project_id,
        episode_ids=[first, second],
    )
    assert [chapter.episode_id for chapter in result.chapters] == [first, second]
    assert [chapter.title for chapter in result.chapters] == ["前", "后"]
    assert all(chapter.skip_reason == "no_layout" for chapter in result.chapters)


def test_other_account_cannot_access_anthology_preview() -> None:
    owner = uuid4()
    stranger = uuid4()
    project_id = uuid4()
    episode_id = uuid4()

    class IsolationSession:
        async def get(self, model: type[object], record_id: object) -> object | None:
            if model is ProjectRecord and record_id == project_id:
                return SimpleNamespace(id=project_id, owner_id=owner)
            return None

        async def scalars(self, query: object) -> SimpleNamespace:
            return SimpleNamespace(all=lambda: [])

    async def signed_in_account() -> SimpleNamespace:
        return SimpleNamespace(id=stranger)

    async def override_session() -> AsyncIterator[IsolationSession]:
        yield IsolationSession()

    app.dependency_overrides[current_account_dependency] = signed_in_account
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[require_rate_limit] = lambda: None
    try:
        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/projects/{project_id}/anthology/preview",
                params=[("episode_ids", str(episode_id))],
                cookies={"manxu_session": "test"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"
