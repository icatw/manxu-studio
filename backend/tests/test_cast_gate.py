from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.api_responses import ApiError
from app.schemas.workspace import PanelImageGenerationRequest
from app.services import storyboard as storyboard_service


@pytest.mark.asyncio
async def test_cast_gate_blocks_without_trial() -> None:
    panel = SimpleNamespace(
        id=uuid4(), episode_id=uuid4(), character_ids=[], current_image_asset_id=None
    )
    episode = SimpleNamespace(id=panel.episode_id, project_id=uuid4())
    body = PanelImageGenerationRequest(instruction="a scene")

    class FakeSession:
        async def get(self, model: object, ident: object) -> object | None:
            if ident == panel.id:
                return panel
            if ident == episode.id:
                return episode
            return None

        async def scalar(self, query: object) -> int:
            return 0

    with pytest.raises(ApiError) as exc:
        await storyboard_service.generate_panel_image(
            FakeSession(),  # type: ignore[arg-type]
            panel_id=panel.id,
            owner_id=uuid4(),
            body=body,
        )
    assert exc.value.code == "CAST_REQUIRED"
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_cast_gate_allows_with_trial_ack(monkeypatch: pytest.MonkeyPatch) -> None:
    panel = SimpleNamespace(
        id=uuid4(), episode_id=uuid4(), character_ids=[], current_image_asset_id=None
    )
    episode = SimpleNamespace(id=panel.episode_id, project_id=uuid4())
    body = PanelImageGenerationRequest(instruction="trial", acknowledge_trial=True)
    created: dict[str, object] = {}

    class FakeSession:
        async def get(self, model: object, ident: object) -> object | None:
            if ident == panel.id:
                return panel
            if ident == episode.id:
                return episode
            return None

        async def scalar(self, query: object) -> int:
            return 0

    async def fake_create_task(session: object, **kwargs: object) -> SimpleNamespace:
        created.update(kwargs)
        return SimpleNamespace(id=uuid4())

    monkeypatch.setattr(storyboard_service, "_create_task", fake_create_task)
    result = await storyboard_service.generate_panel_image(
        FakeSession(),  # type: ignore[arg-type]
        panel_id=panel.id,
        owner_id=uuid4(),
        body=body,
    )
    assert result.id
    assert created.get("task_type") == "panel_image"
