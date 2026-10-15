from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.task_queue import generation_job_id
from app.tasks.checkpoints import strip_resumable_checkpoints
from app.tasks.handlers import story_pipeline as pipeline


def test_generation_job_ids_are_unique_per_enqueue() -> None:
    task_id = uuid4()
    assert generation_job_id(task_id) != generation_job_id(task_id)
    assert generation_job_id(task_id).startswith(f"generation:{task_id}:")


def test_strip_resumable_checkpoints_removes_provider_and_pipeline_state() -> None:
    cleaned = strip_resumable_checkpoints(
        {
            "episode_id": "ep-1",
            "panel_count": 4,
            "provider_jobs": {"scene:1": {"remote_task_id": "old"}},
            "pipeline_stages": {"characters": {"done": True}},
        }
    )
    assert cleaned == {"episode_id": "ep-1", "panel_count": 4}
    assert "provider_jobs" not in cleaned
    assert "pipeline_stages" not in cleaned


@pytest.mark.asyncio
async def test_story_pipeline_skips_completed_stages(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    task = SimpleNamespace(
        request_data={
            "regenerate_characters": True,
            "pipeline_stages": {
                "characters": {
                    "done": True,
                    "character_ids": ["c1"],
                    "warnings": ["kept"],
                },
                "scenes": {"done": True, "scene_ids": ["s1"], "warnings": []},
            },
        }
    )

    async def unexpected_characters(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise AssertionError("characters stage should be skipped")

    async def unexpected_scenes(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise AssertionError("scenes stage should be skipped")

    async def generate_panels(*_args: object, **_kwargs: object) -> dict[str, object]:
        calls.append("storyboard")
        return {"episode_id": "ep-1", "panel_ids": ["p1"]}

    async def report_progress(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(pipeline, "generate_characters", unexpected_characters)
    monkeypatch.setattr(pipeline, "generate_scenes", unexpected_scenes)
    monkeypatch.setattr(pipeline, "generate_panels", generate_panels)
    monkeypatch.setattr(pipeline, "report_progress", report_progress)

    class FakeSession:
        async def commit(self) -> None:
            return None

    result = await pipeline.handle_story_pipeline(FakeSession(), task)  # type: ignore[arg-type]
    assert calls == ["storyboard"]
    assert result["character_ids"] == ["c1"]
    assert result["scene_ids"] == ["s1"]
    assert result["panel_ids"] == ["p1"]
    assert result["warnings"] == ["kept"]
    assert task.request_data["pipeline_stages"]["storyboard"]["done"] is True
