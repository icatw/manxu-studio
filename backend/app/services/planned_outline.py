"""Parse and apply 「规划话大纲」 from world_setting (EP2-OUTLINE-01)."""

from __future__ import annotations

import re
from dataclasses import dataclass

PLACEHOLDER_SYNOPSIS = "待补充本话梗概"

_HEADING_RE = re.compile(
    r"^###\s*第\s*(\d+)\s*话\s*[：:]\s*(.+?)\s*$",
    re.MULTILINE,
)
_GENERIC_TITLE_RE = re.compile(r"^第\s*\d+\s*话$")


@dataclass(frozen=True)
class PlannedChapter:
    episode_number: int
    title: str
    synopsis: str


def parse_planned_chapters(world_setting: str) -> list[PlannedChapter]:
    """Parse appendix written by `_planned_outline_appendix` (chapters 2+)."""
    text = world_setting or ""
    marker = "## 规划话大纲"
    idx = text.find(marker)
    if idx < 0:
        return []
    section = text[idx:]
    matches = list(_HEADING_RE.finditer(section))
    if not matches:
        return []

    chapters: list[PlannedChapter] = []
    for i, match in enumerate(matches):
        number = int(match.group(1))
        if number < 2:
            continue
        title = match.group(2).strip()
        # Plan model sometimes prefixes title with "第N话：" again.
        title = re.sub(rf"^第\s*{number}\s*话\s*[：:]\s*", "", title).strip() or title
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(section)
        body = section[start:end].strip()
        # Drop trailing blank / next section noise
        body_lines = [line for line in body.splitlines() if not line.startswith("## ")]
        synopsis = "\n".join(body_lines).strip()
        chapters.append(PlannedChapter(episode_number=number, title=title, synopsis=synopsis))
    return chapters


def planned_chapter_for(world_setting: str, episode_number: int) -> PlannedChapter | None:
    for chapter in parse_planned_chapters(world_setting):
        if chapter.episode_number == episode_number:
            return chapter
    return None


def is_placeholder_synopsis(synopsis: str) -> bool:
    return synopsis.strip() in {"", PLACEHOLDER_SYNOPSIS}


def is_generic_episode_title(title: str) -> bool:
    return bool(_GENERIC_TITLE_RE.match(title.strip()))


def resolve_episode_seed(
    *,
    episode_number: int,
    title: str,
    synopsis: str,
    project_synopsis: str,
    world_setting: str,
) -> tuple[str, str]:
    """For episode_number >= 2, prefer planned outline; never keep project premise by default."""
    if episode_number < 2:
        return title.strip(), synopsis.strip()

    planned = planned_chapter_for(world_setting, episode_number)
    next_title = title.strip()
    next_synopsis = synopsis.strip()
    copies_project = bool(project_synopsis.strip()) and next_synopsis == project_synopsis.strip()

    if planned is not None:
        if is_placeholder_synopsis(next_synopsis) or copies_project:
            next_synopsis = planned.synopsis.strip() or PLACEHOLDER_SYNOPSIS
        if is_generic_episode_title(next_title) and planned.title.strip():
            next_title = planned.title.strip()
        return next_title, next_synopsis

    if is_placeholder_synopsis(next_synopsis) or copies_project:
        next_synopsis = PLACEHOLDER_SYNOPSIS
    return next_title, next_synopsis
