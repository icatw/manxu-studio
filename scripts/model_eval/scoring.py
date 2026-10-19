"""Deterministic scorers for Manxu generation trajectories."""

from __future__ import annotations

import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class StageScore:
    stage: str
    passed: bool
    checks: dict[str, bool] = field(default_factory=dict)
    detail: str = ""


@dataclass(slots=True)
class TrialScore:
    config_id: str
    case_id: str
    trial: int
    stages: list[StageScore]
    first_failure: str | None
    outcome_pass: bool
    total_latency_ms: int
    text_tokens: int | None
    image_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "config_id": self.config_id,
            "case_id": self.case_id,
            "trial": self.trial,
            "outcome_pass": self.outcome_pass,
            "first_failure": self.first_failure,
            "total_latency_ms": self.total_latency_ms,
            "text_tokens": self.text_tokens,
            "image_count": self.image_count,
            "stages": [asdict(stage) for stage in self.stages],
        }


def normalize_name(name: str) -> str:
    return "".join(unicodedata.normalize("NFKC", name).split()).casefold()


def score_plan(plan: dict[str, Any], *, chapter_count: int) -> StageScore:
    chapters = plan.get("chapters") or []
    characters = plan.get("characters") or []
    checks = {
        "has_title": bool(str(plan.get("title") or "").strip()),
        "has_world": bool(str(plan.get("world_setting") or "").strip()),
        "chapter_count": len(chapters) == chapter_count,
        "has_characters": len(characters) >= 1,
        "characters_have_appearance": all(
            str(item.get("appearance") or "").strip() for item in characters
        ),
    }
    return StageScore(
        stage="plan",
        passed=all(checks.values()),
        checks=checks,
        detail=f"chapters={len(chapters)} characters={len(characters)}",
    )


def score_characters(
    characters: list[dict[str, Any]], *, min_count: int, max_count: int
) -> StageScore:
    checks = {
        "count_in_range": min_count <= len(characters) <= max_count,
        "unique_names": len({normalize_name(str(c.get("name") or "")) for c in characters})
        == len(characters),
        "has_reference_prompt": all(
            str(c.get("reference_image_prompt") or "").strip() for c in characters
        ),
        "has_appearance": all(str(c.get("appearance") or "").strip() for c in characters),
    }
    return StageScore(
        stage="characters",
        passed=all(checks.values()),
        checks=checks,
        detail=f"count={len(characters)}",
    )


def score_scenes(scenes: list[dict[str, Any]], *, min_count: int, max_count: int) -> StageScore:
    checks = {
        "count_in_range": min_count <= len(scenes) <= max_count,
        "has_description": all(str(s.get("description") or "").strip() for s in scenes),
        "has_lighting": all(str(s.get("lighting") or "").strip() for s in scenes),
    }
    return StageScore(
        stage="scenes",
        passed=all(checks.values()),
        checks=checks,
        detail=f"count={len(scenes)}",
    )


def score_storyboard(
    panels: list[dict[str, Any]],
    *,
    panel_count: int,
    cast_names: list[str],
) -> StageScore:
    cast_norms = {normalize_name(name) for name in cast_names if name.strip()}
    named = 0
    bound = 0
    for panel in panels:
        names = [str(item) for item in (panel.get("character_names") or [])]
        if names:
            named += 1
            if all(normalize_name(name) in cast_norms for name in names if name.strip()):
                bound += 1
    checks = {
        "panel_count": len(panels) == panel_count,
        "has_image_prompt": all(str(p.get("image_prompt") or "").strip() for p in panels),
        "has_shot": all(str(p.get("shot") or "").strip() for p in panels),
        "cast_names_resolvable": named == 0 or bound == named,
    }
    return StageScore(
        stage="storyboard",
        passed=all(checks.values()),
        checks=checks,
        detail=f"panels={len(panels)} named={named} bound={bound}",
    )


def score_images(paths: list[str], *, expected: int, stage: str = "images") -> StageScore:
    existing = [path for path in paths if path]
    checks = {
        "expected_count": len(existing) == expected,
        "all_non_empty_paths": len(existing) == len(paths) and expected > 0,
    }
    return StageScore(
        stage=stage,
        passed=all(checks.values()) if expected > 0 else True,
        checks=checks,
        detail=f"got={len(existing)} expected={expected}",
    )


def assemble_trial_score(
    *,
    config_id: str,
    case_id: str,
    trial: int,
    stages: list[StageScore],
    total_latency_ms: int,
    text_tokens: int | None,
    image_count: int,
) -> TrialScore:
    first_failure = next((stage.stage for stage in stages if not stage.passed), None)
    return TrialScore(
        config_id=config_id,
        case_id=case_id,
        trial=trial,
        stages=stages,
        first_failure=first_failure,
        outcome_pass=first_failure is None,
        total_latency_ms=total_latency_ms,
        text_tokens=text_tokens,
        image_count=image_count,
    )


def summarize_scores(trials: list[TrialScore]) -> dict[str, Any]:
    by_key: dict[str, list[TrialScore]] = {}
    for trial in trials:
        key = f"{trial.config_id}::{trial.case_id}"
        by_key.setdefault(key, []).append(trial)

    rows: list[dict[str, Any]] = []
    for key, group in sorted(by_key.items()):
        passes = sum(1 for item in group if item.outcome_pass)
        n = len(group)
        rows.append(
            {
                "key": key,
                "trials": n,
                "pass_at_1": passes / n if n else 0.0,
                "pass_count": passes,
                "avg_latency_ms": int(sum(item.total_latency_ms for item in group) / n) if n else 0,
                "avg_images": sum(item.image_count for item in group) / n if n else 0.0,
                "first_failures": sorted(
                    {item.first_failure for item in group if item.first_failure}
                ),
            }
        )
    return {"groups": rows, "trial_count": len(trials)}
