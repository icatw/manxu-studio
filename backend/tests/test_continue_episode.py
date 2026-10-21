"""SERIAL-AGENT-01 continue_episode orchestration."""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.api_responses import ApiError
from app.db.models import EpisodeRecord, GenerationTaskRecord, ProjectRecord
from app.schemas.workspace import ContinueEpisodeRequest
from app.services import storyboard as storyboard_service
from app.services.episode_frontier import resolve_continue_next
from app.tasks.handlers import continue_episode as continue_handler


def test_resolve_continue_next_frontier() -> None:
    ep1 = SimpleNamespace(id=uuid4(), title="第一话", summary="")
    ep2 = SimpleNamespace(id=uuid4(), title="第二话", summary="有摘要")
    stay = resolve_continue_next([ep1])  # type: ignore[arg-type]
    assert stay.kind == "stay"
    studio = resolve_continue_next([ep2, ep1])  # type: ignore[list-item]
    assert studio.kind == "studio"
    assert resolve_continue_next([ep2]).kind == "create_next"  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_continue_episode_api_rejects_incomplete_frontier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = uuid4()
    owner_id = uuid4()
    episode = EpisodeRecord(
        project_id=project_id,
        position=0,
        title="第一话",
        synopsis="s",
        panel_count=8,
    )
    episode.id = uuid4()
    episode.summary = ""

    class FakeSession:
        async def get(self, model: type[object], record_id: object) -> object | None:
            if model is ProjectRecord and record_id == project_id:
                return SimpleNamespace(id=project_id)
            return None

    async def fake_list(session: object, pid: object) -> list[EpisodeRecord]:
        assert pid == project_id
        return [episode]

    monkeypatch.setattr(storyboard_service, "list_project_episodes_ordered", fake_list)

    with pytest.raises(ApiError) as raised:
        await storyboard_service.continue_episode_generation(
            FakeSession(),  # type: ignore[arg-type]
            project_id=project_id,
            owner_id=owner_id,
            body=ContinueEpisodeRequest(),
        )
    assert raised.value.status_code == 409
    assert "摘要" in raised.value.message


@pytest.mark.asyncio
async def test_continue_episode_handler_creates_episode_without_storyboard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = uuid4()
    task_id = uuid4()
    episode_id = uuid4()
    project = SimpleNamespace(id=project_id, synopsis="", world_setting="")
    created_episode = SimpleNamespace(id=episode_id, title="第 2 话")

    task = GenerationTaskRecord(
        id=task_id,
        owner_id=uuid4(),
        project_id=project_id,
        task_type="continue_episode",
        status="running",
        request_data={"generate_storyboard": False, "panel_count": 8, "use_continuity": True},
    )

    ep1 = EpisodeRecord(
        project_id=project_id, position=0, title="第一话", synopsis="梗概", panel_count=8
    )
    ep1.id = uuid4()
    ep1.summary = "上一话摘要内容足够长了。"

    class FakeSession:
        async def get(self, model: type[object], record_id: object) -> object | None:
            if model is ProjectRecord and record_id == project_id:
                return project
            if model is GenerationTaskRecord and record_id == task_id:
                return task
            if model is EpisodeRecord and record_id == episode_id:
                return created_episode
            return None

        async def commit(self) -> None:
            return None

    async def fake_list(session: object, pid: object) -> list[EpisodeRecord]:
        return [ep1]

    async def fake_create(
        session: object, pid: object, body: object
    ) -> SimpleNamespace:
        assert pid == project_id
        return created_episode

    async def fake_progress(session: object, t: object, progress: int) -> None:
        _ = (session, t, progress)

    monkeypatch.setattr(continue_handler, "list_project_episodes_ordered", fake_list)
    monkeypatch.setattr(continue_handler, "create_episode", fake_create)
    monkeypatch.setattr(continue_handler, "report_progress", fake_progress)

    result = await continue_handler.handle_continue_episode(FakeSession(), task)  # type: ignore[arg-type]
    assert result["episode_id"] == str(episode_id)
    assert result["created"] is True
    assert result["panel_ids"] == []
    assert result["generate_storyboard"] is False
