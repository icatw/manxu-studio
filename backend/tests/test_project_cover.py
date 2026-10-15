from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.db.models import EpisodeRecord, ExportRecord
from app.services.projects import project_cover_image_url as _project_cover_image_url
from app.tasks.handlers.export import handle_export as _create_export


class CoverSession:
    def __init__(self, image_url: str | None) -> None:
        self.image_url = image_url

    async def scalar(self, query: object) -> str | None:
        return self.image_url


@pytest.mark.asyncio
async def test_project_cover_image_url_returns_first_panel_image() -> None:
    record = SimpleNamespace(id=uuid4(), cover_asset_id=None)
    url = await _project_cover_image_url(
        CoverSession("/api/v1/assets/cover.png"),  # type: ignore[arg-type]
        record,  # type: ignore[arg-type]
    )
    assert url == "/api/v1/assets/cover.png"


@pytest.mark.asyncio
async def test_project_cover_prefers_cover_asset_id() -> None:
    asset_id = uuid4()
    record = SimpleNamespace(id=uuid4(), cover_asset_id=asset_id)
    url = await _project_cover_image_url(
        CoverSession("/api/v1/assets/ignored.png"),  # type: ignore[arg-type]
        record,  # type: ignore[arg-type]
    )
    assert url == f"/api/v1/assets/{asset_id}"


@pytest.mark.asyncio
async def test_project_cover_image_url_null_when_missing() -> None:
    record = SimpleNamespace(id=uuid4(), cover_asset_id=None)
    url = await _project_cover_image_url(CoverSession(None), record)  # type: ignore[arg-type]
    assert url is None


@pytest.mark.asyncio
async def test_production_json_export_includes_panel_fields() -> None:
    episode_id = uuid4()
    project_id = uuid4()
    episode = SimpleNamespace(id=episode_id, project_id=project_id, title="第一话", synopsis="开场")
    panel = SimpleNamespace(
        id=uuid4(),
        episode_id=episode_id,
        position=0,
        scene_description="雨夜车站",
        shot="中景",
        composition="主体偏左",
        character_actions="回头",
        emotion="紧张",
        dialogue="来了吗？",
        story_purpose="抛出悬念",
        image_prompt="rainy station",
        review_status="approved",
        current_image_url="/api/v1/assets/p1.png",
        character_ids=[],
    )
    exports: list[ExportRecord] = []

    class FakeSession:
        async def get(self, model: type[object], record_id: object) -> object | None:
            if model is EpisodeRecord and record_id == episode_id:
                return episode
            return None

        async def scalars(self, query: object) -> SimpleNamespace:
            return SimpleNamespace(all=lambda: [panel])

        def add(self, item: ExportRecord) -> None:
            exports.append(item)

        async def flush(self) -> None:
            pass

    task = SimpleNamespace(
        project_id=project_id,
        request_data={
            "episode_id": str(episode_id),
            "format": "production_json",
            "include_unapproved_panels": True,
        },
    )
    result = await _create_export(FakeSession(), task)  # type: ignore[arg-type]
    assert "asset_id" in result
    assert len(exports) == 1
    assert exports[0].content_type == "application/json"
    payload = exports[0].content.decode("utf-8")
    assert "主体偏左" in payload
    assert "抛出悬念" in payload
    assert "rainy station" in payload
