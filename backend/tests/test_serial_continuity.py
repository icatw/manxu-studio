from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.db.models import ProjectRecord
from app.schemas.workspace import PlannedEpisode
from app.services.serial_service import _planned_outline_appendix, build_continuity


def test_planned_outline_appendix_skips_first_chapter() -> None:
    chapters = [
        PlannedEpisode(title="第1话", synopsis="开场"),
        PlannedEpisode(title="雾港重逢", synopsis="旧友现身"),
        PlannedEpisode(title="项链真相", synopsis="伏笔回收"),
    ]
    text = _planned_outline_appendix(chapters)
    assert "规划话大纲" in text
    assert "第2话：雾港重逢" in text
    assert "第3话：项链真相" in text
    assert "开场" not in text


def test_planned_outline_appendix_empty_when_single_chapter() -> None:
    assert _planned_outline_appendix([PlannedEpisode(title="仅一话", synopsis="完")]) == ""


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
