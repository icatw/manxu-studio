from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.routes import generations as generations_routes
from app.schemas.workspace import GenerationProviderResumeRequest
from app.tasks.retry_policy import (
    authorize_provider_resubmit,
    bind_remote_task_id,
    blocks_ordinary_retry,
    requires_resubmit_acknowledgment,
    task_error_code,
)


def test_blocks_ordinary_retry_for_provider_protected_codes() -> None:
    assert blocks_ordinary_retry({"code": "PROVIDER_SUBMIT_AMBIGUOUS"})
    assert blocks_ordinary_retry({"code": "RECOVERY_EXHAUSTED"})
    assert not blocks_ordinary_retry({"code": "TASK_FAILED"})
    assert not blocks_ordinary_retry(None)


def test_bind_remote_task_id_to_single_pending_job() -> None:
    asset_id = str(uuid4())
    request_data = {
        "provider_jobs": {
            "character:1": {"asset_id": asset_id},
        }
    }
    bind_remote_task_id(request_data, remote_task_id="remote-123")
    assert request_data["provider_jobs"]["character:1"]["remote_task_id"] == "remote-123"


def test_bind_remote_task_id_requires_job_key_when_ambiguous() -> None:
    request_data = {
        "provider_jobs": {
            "character:1": {"asset_id": str(uuid4())},
            "scene:1": {"asset_id": str(uuid4())},
        }
    }
    with pytest.raises(ValueError, match="job_key"):
        bind_remote_task_id(request_data, remote_task_id="remote-123")

    bind_remote_task_id(
        request_data,
        remote_task_id="remote-123",
        job_key="scene:1",
    )
    assert request_data["provider_jobs"]["scene:1"]["remote_task_id"] == "remote-123"
    assert request_data["provider_jobs"]["scene:1"]["submission_state"] == "submitted"
    assert "remote_task_id" not in request_data["provider_jobs"]["character:1"]


def test_bind_remote_task_id_rejects_replacing_saved_id() -> None:
    request_data = {
        "provider_jobs": {
            "panel:1": {
                "asset_id": str(uuid4()),
                "remote_task_id": "remote-original",
                "submission_state": "submitted",
            }
        }
    }

    with pytest.raises(ValueError, match="已绑定其他远端任务"):
        bind_remote_task_id(
            request_data,
            remote_task_id="remote-conflicting",
            job_key="panel:1",
        )

    assert request_data["provider_jobs"]["panel:1"]["remote_task_id"] == "remote-original"


def test_explicit_resubmit_acknowledgment_resets_ambiguous_checkpoint() -> None:
    request_data = {
        "provider_jobs": {"panel:1": {"asset_id": str(uuid4()), "submission_state": "submitting"}}
    }
    authorize_provider_resubmit(request_data)
    assert request_data["provider_jobs"]["panel:1"]["submission_state"] == "ready"


def test_saved_remote_id_does_not_require_duplicate_submit_acknowledgment() -> None:
    assert not requires_resubmit_acknowledgment(
        {"provider_jobs": {"panel:1": {"asset_id": "asset", "remote_task_id": "remote"}}}
    )
    assert requires_resubmit_acknowledgment(
        {"provider_jobs": {"panel:1": {"asset_id": "asset", "submission_state": "submitting"}}}
    )


def test_task_error_code_reads_problem_dict() -> None:
    task = SimpleNamespace(error={"code": "RECOVERY_EXHAUSTED", "detail": "x"})
    assert task_error_code(task.error) == "RECOVERY_EXHAUSTED"


@pytest.mark.asyncio
async def test_ordinary_retry_rejects_ambiguous_submit() -> None:
    task_id = uuid4()
    previous = SimpleNamespace(
        id=task_id,
        status="failed",
        error={"code": "PROVIDER_SUBMIT_AMBIGUOUS", "detail": "uncertain"},
        project_id=uuid4(),
        episode_id=None,
        panel_id=None,
        task_type="character_draft",
        request_data={"provider_jobs": {"character:1": {"asset_id": str(uuid4())}}},
    )

    class FakeSession:
        async def get(self, _model: type[object], record_id: object) -> object:
            assert record_id == task_id
            return previous

    request = SimpleNamespace(state=SimpleNamespace(account_id=uuid4()))
    with pytest.raises(HTTPException) as raised:
        await generations_routes.retry_generation_task(
            task_id,
            request,  # type: ignore[arg-type]
            FakeSession(),  # type: ignore[arg-type]
        )
    assert raised.value.status_code == 409
    assert "供应商续跑" in str(raised.value.detail)


@pytest.mark.asyncio
async def test_ordinary_retry_rejects_generic_failure_with_provider_checkpoint() -> None:
    task_id = uuid4()
    previous = SimpleNamespace(
        id=task_id,
        status="failed",
        error={"code": "TASK_FAILED", "detail": "database write failed"},
        project_id=uuid4(),
        episode_id=None,
        panel_id=None,
        task_type="panel_image",
        request_data={
            "provider_jobs": {
                "panel:1": {
                    "asset_id": str(uuid4()),
                    "remote_task_id": "remote-saved",
                    "submission_state": "submitted",
                }
            }
        },
    )

    class FakeSession:
        async def get(self, _model: type[object], record_id: object) -> object:
            assert record_id == task_id
            return previous

    request = SimpleNamespace(state=SimpleNamespace(account_id=uuid4()))
    with pytest.raises(HTTPException) as raised:
        await generations_routes.retry_generation_task(
            task_id,
            request,  # type: ignore[arg-type]
            FakeSession(),  # type: ignore[arg-type]
        )

    assert raised.value.status_code == 409
    assert "供应商续跑" in str(raised.value.detail)


@pytest.mark.asyncio
async def test_provider_resume_binds_remote_and_requeues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = uuid4()
    asset_id = str(uuid4())
    task = SimpleNamespace(
        id=task_id,
        status="failed",
        error={"code": "PROVIDER_SUBMIT_AMBIGUOUS", "detail": "uncertain"},
        request_data={
            "provider_jobs": {"character:1": {"asset_id": asset_id}},
            "recovery_attempts": 4,
        },
        updated_at=None,
    )
    enqueued: list[str] = []

    class FakeSession:
        async def get(self, _model: type[object], record_id: object) -> object:
            assert record_id == task_id
            return task

        async def commit(self) -> None:
            return None

        async def refresh(self, _item: object) -> None:
            return None

    async def enqueue(task_ref: object, *, reclaim_if_blocked: bool = False) -> bool:
        enqueued.append(str(task_ref))
        assert reclaim_if_blocked is True
        return True

    monkeypatch.setattr(generations_routes, "enqueue_generation_task", enqueue)
    monkeypatch.setattr(
        generations_routes,
        "_task_view",
        lambda item: SimpleNamespace(id=item.id, status=item.status),
    )

    result = await generations_routes.resume_provider_generation_task(
        task_id,
        GenerationProviderResumeRequest(remote_task_id="remote-abc"),
        FakeSession(),  # type: ignore[arg-type]
    )
    assert task.status == "queued"
    assert task.error is None
    assert task.request_data["recovery_attempts"] == 0
    assert task.request_data["provider_jobs"]["character:1"]["remote_task_id"] == "remote-abc"
    assert enqueued == [str(task_id)]
    assert result.status == "queued"


@pytest.mark.asyncio
async def test_provider_resume_requires_ack_without_remote_id() -> None:
    task_id = uuid4()
    task = SimpleNamespace(
        id=task_id,
        status="failed",
        error={"code": "PROVIDER_SUBMIT_AMBIGUOUS"},
        request_data={"provider_jobs": {"character:1": {"asset_id": str(uuid4())}}},
    )

    class FakeSession:
        async def get(self, _model: type[object], record_id: object) -> object:
            return task

    with pytest.raises(HTTPException) as raised:
        await generations_routes.resume_provider_generation_task(
            task_id,
            GenerationProviderResumeRequest(acknowledge_resubmit=False),
            FakeSession(),  # type: ignore[arg-type]
        )
    assert raised.value.status_code == 409
    assert "acknowledge_resubmit" in str(raised.value.detail)


@pytest.mark.asyncio
async def test_provider_resume_acknowledgment_resets_checkpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = uuid4()
    task = SimpleNamespace(
        id=task_id,
        status="failed",
        error={"code": "PROVIDER_SUBMIT_AMBIGUOUS"},
        request_data={
            "provider_jobs": {
                "panel:1": {"asset_id": str(uuid4()), "submission_state": "submitting"}
            }
        },
        updated_at=None,
    )

    class FakeSession:
        async def get(self, _model: type[object], record_id: object) -> object:
            return task

        async def commit(self) -> None:
            return None

        async def refresh(self, _item: object) -> None:
            return None

    async def enqueue(_task_ref: object, *, reclaim_if_blocked: bool = False) -> bool:
        assert reclaim_if_blocked is True
        return True

    monkeypatch.setattr(generations_routes, "enqueue_generation_task", enqueue)
    monkeypatch.setattr(
        generations_routes,
        "_task_view",
        lambda item: SimpleNamespace(id=item.id, status=item.status),
    )
    await generations_routes.resume_provider_generation_task(
        task_id,
        GenerationProviderResumeRequest(acknowledge_resubmit=True),
        FakeSession(),  # type: ignore[arg-type]
    )

    assert task.status == "queued"
    assert task.request_data["provider_jobs"]["panel:1"]["submission_state"] == "ready"


@pytest.mark.asyncio
async def test_provider_resume_uses_runtime_persisted_remote_id_without_ack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = uuid4()
    task = SimpleNamespace(
        id=task_id,
        status="failed",
        error={"code": "TASK_FAILED", "detail": "result commit failed"},
        request_data={
            "provider_jobs": {
                "panel:1": {
                    "asset_id": str(uuid4()),
                    "remote_task_id": "remote-saved-by-runtime",
                    "submission_state": "submitted",
                }
            }
        },
        updated_at=None,
    )

    class FakeSession:
        async def get(self, _model: type[object], record_id: object) -> object:
            return task

        async def commit(self) -> None:
            return None

        async def refresh(self, _item: object) -> None:
            return None

    async def enqueue(_task_ref: object, *, reclaim_if_blocked: bool = False) -> bool:
        assert reclaim_if_blocked is True
        return True

    monkeypatch.setattr(generations_routes, "enqueue_generation_task", enqueue)
    monkeypatch.setattr(
        generations_routes,
        "_task_view",
        lambda item: SimpleNamespace(id=item.id, status=item.status),
    )
    result = await generations_routes.resume_provider_generation_task(
        task_id,
        GenerationProviderResumeRequest(),
        FakeSession(),  # type: ignore[arg-type]
    )
    assert task.status == "queued"
    assert task.request_data["provider_jobs"]["panel:1"]["remote_task_id"] == (
        "remote-saved-by-runtime"
    )
    assert result.status == "queued"
