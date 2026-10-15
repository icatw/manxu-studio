from types import SimpleNamespace
from uuid import uuid4

import pytest
from arq.constants import in_progress_key_prefix, job_key_prefix, result_key_prefix

from app.services import task_queue
from app.services.task_queue import primary_generation_job_id
from app.tasks.checkpoints import strip_resumable_checkpoints
from app.tasks.handlers import story_pipeline as pipeline
from app.tasks.provider_jobs import clear_image_job, persist_text_checkpoint, text_checkpoint


def test_primary_generation_job_id_is_stable() -> None:
    task_id = uuid4()
    assert primary_generation_job_id(task_id) == primary_generation_job_id(task_id)
    assert primary_generation_job_id(task_id) == f"generation:{task_id}"


def test_strip_resumable_checkpoints_removes_provider_pipeline_and_text_state() -> None:
    cleaned = strip_resumable_checkpoints(
        {
            "episode_id": "ep-1",
            "panel_count": 4,
            "provider_jobs": {"scene:1": {"remote_task_id": "old"}},
            "pipeline_stages": {"characters": {"done": True}},
            "text_checkpoints": {"characters": {"done": True, "character_ids": ["c1"]}},
            "recovery_attempts": 3,
        }
    )
    assert cleaned == {"episode_id": "ep-1", "panel_count": 4}
    assert "provider_jobs" not in cleaned
    assert "pipeline_stages" not in cleaned
    assert "text_checkpoints" not in cleaned
    assert "recovery_attempts" not in cleaned


@pytest.mark.asyncio
async def test_enqueue_skips_reclaim_while_primary_job_inflight(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = uuid4()
    primary_id = primary_generation_job_id(task_id)
    calls: list[str] = []

    class FakePool:
        async def enqueue_job(self, *_args: object, **kwargs: object) -> None:
            calls.append(str(kwargs.get("_job_id")))
            return None

        async def exists(self, key: str) -> bool:
            return key == job_key_prefix + primary_id

        async def delete(self, *_args: object) -> None:
            raise AssertionError("must not delete while job is in flight")

    async def fake_pool() -> FakePool:
        return FakePool()

    monkeypatch.setattr(task_queue, "get_arq_pool", fake_pool)
    assert await task_queue.enqueue_generation_task(task_id, reclaim_if_blocked=True) is False
    assert calls == [primary_id]


@pytest.mark.asyncio
async def test_enqueue_skips_reclaim_while_in_progress(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = uuid4()
    primary_id = primary_generation_job_id(task_id)

    class FakePool:
        async def enqueue_job(self, *_args: object, **_kwargs: object) -> None:
            return None

        async def exists(self, key: str) -> bool:
            return key == in_progress_key_prefix + primary_id

        async def delete(self, *_args: object) -> None:
            raise AssertionError("must not delete while in progress")

    async def fake_pool() -> FakePool:
        return FakePool()

    monkeypatch.setattr(task_queue, "get_arq_pool", fake_pool)
    assert await task_queue.enqueue_generation_task(task_id, reclaim_if_blocked=True) is False


@pytest.mark.asyncio
async def test_enqueue_reclaims_by_clearing_result_key_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = uuid4()
    primary_id = primary_generation_job_id(task_id)
    deleted: list[str] = []
    enqueued: list[str] = []

    class FakeJob:
        pass

    class FakePool:
        async def enqueue_job(self, *_args: object, **kwargs: object) -> FakeJob | None:
            job_id = str(kwargs.get("_job_id"))
            enqueued.append(job_id)
            # First attempt blocked by result key; second succeeds after delete.
            return FakeJob() if len(enqueued) > 1 else None

        async def exists(self, key: str) -> bool:
            return key == result_key_prefix + primary_id and not deleted

        async def delete(self, key: str) -> None:
            deleted.append(key)

    async def fake_pool() -> FakePool:
        return FakePool()

    monkeypatch.setattr(task_queue, "get_arq_pool", fake_pool)
    assert await task_queue.enqueue_generation_task(task_id, reclaim_if_blocked=True) is True
    assert deleted == [result_key_prefix + primary_id]
    assert enqueued == [primary_id, primary_id]


@pytest.mark.asyncio
async def test_clear_image_job_and_text_checkpoint_roundtrip() -> None:
    task = SimpleNamespace(
        request_data={
            "provider_jobs": {
                "character:c1": {"asset_id": "a1", "remote_task_id": "remote-old"},
            }
        }
    )

    class FakeSession:
        async def commit(self) -> None:
            return None

    await clear_image_job(FakeSession(), task, "character:c1")  # type: ignore[arg-type]
    assert task.request_data["provider_jobs"] == {}

    await persist_text_checkpoint(
        FakeSession(),  # type: ignore[arg-type]
        task,
        "characters",
        {"character_ids": ["c1"]},
    )
    assert text_checkpoint(task, "characters") == {
        "done": True,
        "character_ids": ["c1"],
    }


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
