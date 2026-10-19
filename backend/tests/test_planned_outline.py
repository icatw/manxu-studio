from app.services.planned_outline import (
    PLACEHOLDER_SYNOPSIS,
    parse_planned_chapters,
    resolve_episode_seed,
)
from app.services.serial_service import _planned_outline_appendix
from app.schemas.workspace import PlannedEpisode


def test_parse_planned_chapters_roundtrip() -> None:
    appendix = _planned_outline_appendix(
        [
            PlannedEpisode(title="开场", synopsis="第一话内容"),
            PlannedEpisode(title="雾港重逢", synopsis="旧友现身"),
            PlannedEpisode(title="第3话：项链真相", synopsis="伏笔回收"),
        ]
    )
    chapters = parse_planned_chapters(f"世界观正文\n{appendix}")
    assert [c.episode_number for c in chapters] == [2, 3]
    assert chapters[0].title == "雾港重逢"
    assert chapters[0].synopsis == "旧友现身"
    assert chapters[1].title == "项链真相"
    assert chapters[1].synopsis == "伏笔回收"


def test_resolve_prefers_planned_over_project_copy() -> None:
    world = (
        "## 规划话大纲（尚未开作）\n\n"
        "### 第2话：完美算法\n"
        "黑客竞赛与苏青登场。\n"
    )
    title, synopsis = resolve_episode_seed(
        episode_number=2,
        title="第 2 话",
        synopsis="作品总梗概开场",
        project_synopsis="作品总梗概开场",
        world_setting=world,
    )
    assert title == "完美算法"
    assert "苏青" in synopsis


def test_resolve_without_plan_rejects_project_copy() -> None:
    title, synopsis = resolve_episode_seed(
        episode_number=2,
        title="第 2 话",
        synopsis="作品总梗概开场",
        project_synopsis="作品总梗概开场",
        world_setting="只有世界观",
    )
    assert title == "第 2 话"
    assert synopsis == PLACEHOLDER_SYNOPSIS


def test_resolve_keeps_author_synopsis() -> None:
    world = (
        "## 规划话大纲（尚未开作）\n\n"
        "### 第2话：完美算法\n"
        "规划原文。\n"
    )
    title, synopsis = resolve_episode_seed(
        episode_number=2,
        title="我的第2话",
        synopsis="作者手改的本话梗概",
        project_synopsis="作品总梗概开场",
        world_setting=world,
    )
    assert title == "我的第2话"
    assert synopsis == "作者手改的本话梗概"
