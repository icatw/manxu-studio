from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.db.models import EpisodeRecord
from app.services.continuity_gate import require_previous_episode_summary


@pytest.mark.asyncio
async def test_first_episode_skips_summary_gate() -> None:
    episode = EpisodeRecord(project_id=uuid4(), title="第一话", synopsis="a", position=0)
    episode.id = uuid4()

    class FakeSession:
        async def scalar(self, query: object) -> None:
            return None

    await require_previous_episode_summary(FakeSession(), episode)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_next_episode_requires_previous_summary() -> None:
    project_id = uuid4()
    previous = SimpleNamespace(id=uuid4(), title="第一话", summary="", position=0)
    current = EpisodeRecord(project_id=project_id, title="第二话", synopsis="b", position=1)
    current.id = uuid4()

    class FakeSession:
        async def scalar(self, query: object) -> object:
            return previous

    with pytest.raises(HTTPException) as error:
        await require_previous_episode_summary(FakeSession(), current)  # type: ignore[arg-type]
    assert error.value.status_code == 409
    assert "第一话" in str(error.value.detail)


@pytest.mark.asyncio
async def test_next_episode_ok_when_previous_has_summary() -> None:
    previous = SimpleNamespace(id=uuid4(), title="第一话", summary="前情提要", position=0)
    current = EpisodeRecord(project_id=uuid4(), title="第二话", synopsis="b", position=1)
    current.id = uuid4()

    class FakeSession:
        async def scalar(self, query: object) -> object:
            return previous

    await require_previous_episode_summary(FakeSession(), current)  # type: ignore[arg-type]
