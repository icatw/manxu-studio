from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.db.models import ProjectRecord
from app.services.serial_service import build_continuity


@pytest.mark.asyncio
async def test_build_continuity_includes_summaries_and_open_threads() -> None:
    project_id = uuid4()
    episode_a = SimpleNamespace(
        id=uuid4(), project_id=project_id, position=0, title="第一话", summary="开场埋下项链"
    )
    episode_b = SimpleNamespace(
        id=uuid4(), project_id=project_id, position=1, title="第二话", summary=""
    )
    thread = SimpleNamespace(
        id=uuid4(),
        project_id=project_id,
        text="项链来历",
        payoff_in_episode_id=None,
        resolved=False,
    )
    project = SimpleNamespace(id=project_id, world_setting="雾港")

    class FakeSession:
        async def get(self, model: type[object], record_id: object) -> object | None:
            if model is ProjectRecord and record_id == project_id:
                return project
            return None

        async def scalars(self, query: object) -> SimpleNamespace:
            query_str = str(query)
            if "plot_threads" in query_str or "PlotThread" in query_str:
                return SimpleNamespace(all=lambda: [thread])
            return SimpleNamespace(all=lambda: [episode_a, episode_b])

    result = await build_continuity(FakeSession(), project_id)  # type: ignore[arg-type]
    assert result.world_setting == "雾港"
    assert len(result.previous_summaries) == 1
    assert result.previous_summaries[0].title == "第一话"
    assert len(result.open_threads) == 1
    assert result.open_threads[0].text == "项链来历"
