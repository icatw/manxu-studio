"""SB-01 reader-language lock: prompt regression + post-generation guard."""

import pytest

from app.tasks.prompts import STORYBOARD_DRAFT, STORYBOARD_READER_LANGUAGE_RULE
from app.tasks.schemas import GeneratedPanel, StoryboardGenerationOutput
from app.tasks.storyboard_language import (
    assert_storyboard_reader_language,
    reader_text_is_acceptable_chinese,
)


def _panel(**overrides: str) -> GeneratedPanel:
    base = {
        "shot": "中景",
        "scene_description": "宿舍夜色，屏幕冷光。",
        "composition": "人物居中，UI 叠层在侧。",
        "character_actions": "林深盯着视网膜警告。",
        "emotion": "紧张",
        "dialogue": "Eve：检测到陷阱。",
        "story_purpose": "建立危机。",
        "image_prompt": "cyberpunk dorm room, blue HUD overlay, cinematic lighting",
        "scene_name": "宿舍",
        "character_names": ["林深", "Eve"],
    }
    base.update(overrides)
    return GeneratedPanel(**base)


def test_storyboard_prompt_locks_simplified_chinese() -> None:
    assert "简体中文" in STORYBOARD_READER_LANGUAGE_RULE
    assert "image_prompt" in STORYBOARD_READER_LANGUAGE_RULE
    assert STORYBOARD_READER_LANGUAGE_RULE in STORYBOARD_DRAFT.system
    assert STORYBOARD_DRAFT.version.startswith("2026-10-20")


def test_reader_text_accepts_chinese_and_empty() -> None:
    assert reader_text_is_acceptable_chinese("")
    assert reader_text_is_acceptable_chinese("Eve：检测到陷阱。")
    assert reader_text_is_acceptable_chinese("无对白。")
    assert reader_text_is_acceptable_chinese("Eve")  # short name fragment


def test_reader_text_rejects_long_english_script() -> None:
    assert not reader_text_is_acceptable_chinese(
        "Eve: 'Warning. Trap detected. Probability of data corruption: 99%.'"
    )
    assert not reader_text_is_acceptable_chinese(
        "Virtual Retina UI. Lin Shen is deep in the cyber-space."
    )


def test_assert_accepts_chinese_panels() -> None:
    assert_storyboard_reader_language(
        StoryboardGenerationOutput(panels=[_panel(), _panel(dialogue="")])
    )


def test_assert_rejects_english_dialogue_like_episode_four() -> None:
    output = StoryboardGenerationOutput(
        panels=[
            _panel(
                dialogue="Eve: 'Warning. Trap detected. Probability of data corruption: 99%.'",
                scene_description=(
                    "Virtual Retina UI. Lin Shen is deep in the cyber-space, "
                    "hacking into Black Shield Tech's servers."
                ),
            )
        ]
    )
    with pytest.raises(ValueError, match="简体中文"):
        assert_storyboard_reader_language(output)


def test_assert_allows_english_image_prompt_only() -> None:
    assert_storyboard_reader_language(
        StoryboardGenerationOutput(
            panels=[
                _panel(
                    image_prompt=("close-up of young man with glitching HUD, neon blue, no text")
                )
            ]
        )
    )
