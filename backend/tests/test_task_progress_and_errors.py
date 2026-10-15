from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.providers.errors import RecoverableProviderError
from app.tasks import runtime
from app.tasks.provider_jobs import bind_image_job
from app.tasks.support import report_progress


@pytest.mark.asyncio
async def test_report_progress_is_monotonic() -> None:
    task = SimpleNamespace(progress=60, updated_at=None)

    class FakeSession:
        async def commit(self) -> None:
            return None

    await report_progress(FakeSession(), task, 40)  # type: ignore[arg-type]
    assert task.progress == 60
    await report_progress(FakeSession(), task, 80)  # type: ignore[arg-type]
    assert task.progress == 80


@pytest.mark.asyncio
async def test_bind_image_job_persists_remote_task_id() -> None:
    task = SimpleNamespace(request_data={})
    commits: list[str] = []

    class FakeSession:
        async def commit(self) -> None:
            commits.append("commit")

    asset_id, resume, on_submitted = await bind_image_job(
        FakeSession(),
        task,
        "scene:abc",  # type: ignore[arg-type]
    )
    assert resume is None
    assert task.request_data["provider_jobs"]["scene:abc"]["asset_id"] == str(asset_id)
    await on_submitted("remote-1")
    assert task.request_data["provider_jobs"]["scene:abc"]["remote_task_id"] == "remote-1"

    asset_id2, resume2, _ = await bind_image_job(
        FakeSession(),
        task,
        "scene:abc",  # type: ignore[arg-type]
    )
    assert asset_id2 == asset_id
    assert resume2 == "remote-1"
    assert len(commits) >= 2


@pytest.mark.asyncio
async def test_runtime_requeues_recoverable_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = uuid4()
    task = SimpleNamespace(
        id=task_id,
        status="running",
        task_type="character_draft",
        project_id=uuid4(),
        owner_id=uuid4(),
        progress=55,
        request_data={"provider_jobs": {"character:1": {"remote_task_id": "keep-me"}}},
        updated_at=None,
        result=None,
        error=None,
    )
    project = SimpleNamespace(owner_id=task.owner_id)
    interrupted: list[str] = []

    class FakeLockConnection:
        async def scalar(self, _query: object) -> bool:
            return True

        async def execute(self, _query: object) -> None:
            return None

        async def __aenter__(self) -> "FakeLockConnection":
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

    class FakeEngine:
        def connect(self) -> FakeLockConnection:
            return FakeLockConnection()

    class FakeSession:
        async def get(self, model: type[object], record_id: object) -> object | None:
            name = getattr(model, "__name__", "")
            if name == "GenerationTaskRecord":
                return task
            if name == "ProjectRecord":
                return project
            return None

        async def commit(self) -> None:
            return None

        async def __aenter__(self) -> "FakeSession":
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

    async def handler(_session: object, _task: object) -> dict[str, object]:
        raise RecoverableProviderError("查询 Qwen Image 任务失败（HTTP 503）")

    async def mark_interrupted(marked_id: object) -> None:
        interrupted.append(str(marked_id))
        task.status = "queued"

    monkeypatch.setattr(runtime, "engine", FakeEngine())
    monkeypatch.setattr(runtime, "SessionFactory", FakeSession)
    monkeypatch.setattr(runtime, "get_handler", lambda _task_type: handler)
    monkeypatch.setattr(runtime, "_mark_interrupted", mark_interrupted)

    await runtime.run_generation_task(task_id)

    assert interrupted == [str(task_id)]
    assert task.status == "queued"
    assert task.error is None
    assert task.request_data["provider_jobs"]["character:1"]["remote_task_id"] == "keep-me"
