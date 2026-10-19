"""Pure scoring tests for scripts/model_eval (no live providers)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from model_eval.scoring import (  # noqa: E402
    assemble_trial_score,
    score_characters,
    score_images,
    score_plan,
    score_scenes,
    score_storyboard,
    summarize_scores,
)


def test_score_plan_chapter_count() -> None:
    ok = score_plan(
        {
            "title": "t",
            "world_setting": "w",
            "characters": [{"appearance": "a"}],
            "chapters": [{"title": "1"}, {"title": "2"}],
        },
        chapter_count=2,
    )
    assert ok.passed
    bad = score_plan(
        {
            "title": "t",
            "world_setting": "w",
            "characters": [{"appearance": "a"}],
            "chapters": [{"title": "1"}],
        },
        chapter_count=2,
    )
    assert not bad.passed
    assert bad.checks["chapter_count"] is False


def test_score_storyboard_cast_binding() -> None:
    panels = [
        {
            "shot": "中景",
            "image_prompt": "p",
            "character_names": ["林夏"],
        },
        {
            "shot": "远景",
            "image_prompt": "p",
            "character_names": [],
        },
    ]
    assert score_storyboard(panels, panel_count=2, cast_names=["林夏", "周澄"]).passed
    bad = score_storyboard(
        [{**panels[0], "character_names": ["不存在的人"]}, panels[1]],
        panel_count=2,
        cast_names=["林夏", "周澄"],
    )
    assert not bad.passed


def test_score_characters_unique_names() -> None:
    chars = [
        {
            "name": "A",
            "appearance": "x",
            "reference_image_prompt": "p",
        },
        {
            "name": "A",
            "appearance": "y",
            "reference_image_prompt": "q",
        },
    ]
    assert not score_characters(chars, min_count=2, max_count=4).passed


def test_score_scenes_and_images() -> None:
    scenes = [
        {"description": "d", "lighting": "l"},
        {"description": "d2", "lighting": "l2"},
    ]
    assert score_scenes(scenes, min_count=1, max_count=3).passed
    assert score_images(["/a.png", "/b.png"], expected=2, stage="char_images").passed
    assert not score_images(["/a.png", ""], expected=2).passed


def test_summarize_pass_at_k() -> None:
    stages_ok = [
        score_plan(
            {
                "title": "t",
                "world_setting": "w",
                "characters": [{"appearance": "a"}],
                "chapters": [{"title": "1"}],
            },
            chapter_count=1,
        )
    ]
    t1 = assemble_trial_score(
        config_id="baseline",
        case_id="A-duo",
        trial=1,
        stages=stages_ok,
        total_latency_ms=100,
        text_tokens=10,
        image_count=0,
    )
    t2 = assemble_trial_score(
        config_id="baseline",
        case_id="A-duo",
        trial=2,
        stages=[
            score_plan(
                {
                    "title": "",
                    "world_setting": "w",
                    "characters": [{"appearance": "a"}],
                    "chapters": [{"title": "1"}],
                },
                chapter_count=1,
            )
        ],
        total_latency_ms=200,
        text_tokens=None,
        image_count=0,
    )
    summary = summarize_scores([t1, t2])
    group = summary["groups"][0]
    assert group["pass_count"] == 1
    assert group["pass_at_1"] == pytest.approx(0.5)
