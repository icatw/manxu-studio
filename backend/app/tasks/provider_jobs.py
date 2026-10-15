"""Durable checkpoints for external provider jobs inside generation task.request_data."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.db.models import GenerationTaskRecord
from app.providers.errors import (
    AmbiguousProviderSubmitError,
    ProviderCheckpointError,
)

OnSubmitStarted = Callable[[], Awaitable[None]]
OnSubmitRejected = Callable[[], Awaitable[None]]
OnSubmitted = Callable[[str], Awaitable[None]]


@dataclass(frozen=True)
class ImageJobCheckpoint:
    asset_id: UUID
    resume_task_id: str | None
    on_submit_started: OnSubmitStarted
    on_submit_rejected: OnSubmitRejected
    on_submitted: OnSubmitted


def _provider_jobs(task: GenerationTaskRecord) -> dict[str, Any]:
    request_data = getattr(task, "request_data", None)
    if not isinstance(request_data, dict):
        request_data = {}
        task.request_data = request_data
    raw = request_data.get("provider_jobs")
    if not isinstance(raw, dict):
        jobs: dict[str, Any] = {}
        request_data["provider_jobs"] = jobs
        return jobs
    return cast(dict[str, Any], raw)


def _mark_request_data_dirty(task: GenerationTaskRecord) -> None:
    try:
        flag_modified(task, "request_data")
    except Exception:
        # Unit-test fakes are not SQLAlchemy instances.
        return


async def clear_image_job(
    session: AsyncSession,
    task: GenerationTaskRecord,
    job_key: str,
) -> None:
    """Drop a provider image checkpoint so a new text snapshot cannot resume a stale remote job."""
    jobs = _provider_jobs(task)
    if job_key not in jobs:
        return
    del jobs[job_key]
    _mark_request_data_dirty(task)
    await session.commit()


def text_checkpoint(task: GenerationTaskRecord, stage: str) -> dict[str, Any] | None:
    request_data = getattr(task, "request_data", None)
    if not isinstance(request_data, dict):
        return None
    raw = request_data.get("text_checkpoints")
    if not isinstance(raw, dict):
        return None
    stage_data = raw.get(stage)
    if isinstance(stage_data, dict) and stage_data.get("done"):
        return cast(dict[str, Any], stage_data)
    return None


async def persist_text_checkpoint(
    session: AsyncSession,
    task: GenerationTaskRecord,
    stage: str,
    payload: dict[str, Any],
) -> None:
    request_data = getattr(task, "request_data", None)
    if not isinstance(request_data, dict):
        request_data = {}
        task.request_data = request_data
    raw = request_data.get("text_checkpoints")
    if not isinstance(raw, dict):
        raw = {}
        request_data["text_checkpoints"] = raw
    raw[stage] = {"done": True, **payload}
    _mark_request_data_dirty(task)
    await session.commit()


async def bind_image_job(
    session: AsyncSession,
    task: GenerationTaskRecord,
    job_key: str,
) -> ImageJobCheckpoint:
    """Create callbacks that durably fence each billable provider submission."""
    jobs = _provider_jobs(task)
    existing = jobs.get(job_key)
    if isinstance(existing, dict) and existing.get("asset_id"):
        asset_id = UUID(str(existing["asset_id"]))
        resume = str(existing["remote_task_id"]) if existing.get("remote_task_id") else None
        submission_state = existing.get("submission_state")
        if resume is None and submission_state != "ready":
            raise AmbiguousProviderSubmitError(
                "图像提交状态不确定；为避免重复计费，系统已停止自动重新提交",
                job_key=job_key,
                asset_id=str(asset_id),
            )
    else:
        asset_id = uuid4()
        resume = None
        jobs[job_key] = {"asset_id": str(asset_id), "submission_state": "ready"}
        _mark_request_data_dirty(task)
        await session.commit()

    async def persist_checkpoint() -> None:
        _mark_request_data_dirty(task)
        await session.commit()

    async def on_submit_started() -> None:
        jobs[job_key] = {"asset_id": str(asset_id), "submission_state": "submitting"}
        try:
            await persist_checkpoint()
        except Exception as error:
            raise ProviderCheckpointError("无法保存图像提交检查点，供应商请求尚未发送") from error

    async def on_submit_rejected() -> None:
        jobs[job_key] = {"asset_id": str(asset_id), "submission_state": "ready"}
        try:
            await persist_checkpoint()
        except Exception as error:
            raise ProviderCheckpointError("供应商拒绝了图像请求，但无法保存安全重试状态") from error

    async def on_submitted(remote_task_id: str) -> None:
        jobs[job_key] = {
            "asset_id": str(asset_id),
            "remote_task_id": remote_task_id,
            "submission_state": "submitted",
        }
        try:
            await persist_checkpoint()
        except Exception as error:
            raise AmbiguousProviderSubmitError(
                "供应商已受理图像任务，但远端任务编号未能保存；为避免重复计费，系统已停止自动重新提交",
                remote_task_id=remote_task_id,
                job_key=job_key,
                asset_id=str(asset_id),
            ) from error

    return ImageJobCheckpoint(
        asset_id=asset_id,
        resume_task_id=resume,
        on_submit_started=on_submit_started,
        on_submit_rejected=on_submit_rejected,
        on_submitted=on_submitted,
    )
