from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.providers.errors import AmbiguousProviderSubmitError, RecoverableProviderError
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


def _runtime_fakes(
    monkeypatch: pytest.MonkeyPatch,
    *,
    task: SimpleNamespace,
    project: SimpleNamespace,
    handler_error: BaseException,
) -> None:
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
        raise handler_error

    monkeypatch.setattr(runtime, "engine", FakeEngine())
    monkeypatch.setattr(runtime, "SessionFactory", FakeSession)
    monkeypatch.setattr(runtime, "get_handler", lambda _task_type: handler)


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
    _runtime_fakes(
        monkeypatch,
        task=task,
        project=project,
        handler_error=RecoverableProviderError("查询 Qwen Image 任务失败（HTTP 503）"),
    )

    await runtime.run_generation_task(task_id)

    assert task.status == "queued"
    assert task.request_data["recovery_attempts"] == 1
    assert task.error is not None
    assert task.error["code"] == "RECOVERING"
    assert task.request_data["provider_jobs"]["character:1"]["remote_task_id"] == "keep-me"


@pytest.mark.asyncio
async def test_runtime_fails_after_recovery_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    task_id = uuid4()
    task = SimpleNamespace(
        id=task_id,
        status="running",
        task_type="character_draft",
        project_id=uuid4(),
        owner_id=uuid4(),
        progress=55,
        request_data={"recovery_attempts": runtime.MAX_RECOVERY_ATTEMPTS},
        updated_at=None,
        result=None,
        error=None,
    )
    project = SimpleNamespace(owner_id=task.owner_id)
    _runtime_fakes(
        monkeypatch,
        task=task,
        project=project,
        handler_error=RecoverableProviderError("still failing"),
    )

    await runtime.run_generation_task(task_id)

    assert task.status == "failed"
    assert task.request_data["recovery_attempts"] == runtime.MAX_RECOVERY_ATTEMPTS + 1
    assert task.error is not None
    assert task.error["code"] == "RECOVERY_EXHAUSTED"


@pytest.mark.asyncio
async def test_runtime_fails_ambiguous_submit_without_requeue(
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
        request_data={"provider_jobs": {"character:1": {"asset_id": str(uuid4())}}},
        updated_at=None,
        result=None,
        error=None,
    )
    project = SimpleNamespace(owner_id=task.owner_id)
    _runtime_fakes(
        monkeypatch,
        task=task,
        project=project,
        handler_error=AmbiguousProviderSubmitError("提交结果不确定"),
    )

    await runtime.run_generation_task(task_id)

    assert task.status == "failed"
    assert task.error is not None
    assert task.error["code"] == "PROVIDER_SUBMIT_AMBIGUOUS"
    assert "recovery_attempts" not in task.request_data
