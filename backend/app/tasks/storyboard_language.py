"""Guard reader-facing storyboard fields stay in Simplified Chinese."""

from __future__ import annotations

import re

from app.tasks.schemas import GeneratedPanel, StoryboardGenerationOutput

_CJK = re.compile(r"[\u4e00-\u9fff]")
_READER_FIELDS = (
    "shot",
    "scene_description",
    "composition",
    "character_actions",
    "emotion",
    "dialogue",
    "story_purpose",
    "scene_name",
)


def reader_text_is_acceptable_chinese(text: str) -> bool:
    """Empty OK; any CJK OK; short Latin fragments OK; long Latin-only fails."""
    cleaned = text.strip()
    if not cleaned:
        return True
    if _CJK.search(cleaned):
        return True
    letters = sum(1 for char in cleaned if char.isalpha())
    return letters < 12


def assert_storyboard_reader_language(output: StoryboardGenerationOutput) -> None:
    """Raise ValueError when reader-facing panel fields look English-only."""
    problems: list[str] = []
    for index, panel in enumerate(output.panels, start=1):
        for field in _READER_FIELDS:
            value = getattr(panel, field)
            if not isinstance(value, str):
                continue
            if reader_text_is_acceptable_chinese(value):
                continue
            preview = value.strip().replace("\n", " ")
            if len(preview) > 48:
                preview = f"{preview[:48]}…"
            problems.append(f"第{index}格.{field}={preview!r}")
    if problems:
        raise ValueError(
            "分镜面向读者的字段须为简体中文（仅 image_prompt 可用英文）。"
            f"请重试。问题字段：{'; '.join(problems[:6])}"
        )


def panel_reader_fields(panel: GeneratedPanel) -> dict[str, str]:
    return {field: str(getattr(panel, field) or "") for field in _READER_FIELDS}
