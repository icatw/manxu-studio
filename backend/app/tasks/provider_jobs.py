"""Durable checkpoints for external provider jobs inside generation task.request_data."""

from collections.abc import Awaitable, Callable
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.db.models import GenerationTaskRecord

OnSubmitted = Callable[[str], Awaitable[None]]


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
) -> tuple[UUID, str | None, OnSubmitted]:
    """Return asset_id, optional remote task id to resume, and a submit checkpoint callback."""
    jobs = _provider_jobs(task)
    existing = jobs.get(job_key)
    if isinstance(existing, dict) and existing.get("asset_id"):
        asset_id = UUID(str(existing["asset_id"]))
        resume = str(existing["remote_task_id"]) if existing.get("remote_task_id") else None
    else:
        asset_id = uuid4()
        resume = None
        jobs[job_key] = {"asset_id": str(asset_id)}
        _mark_request_data_dirty(task)
        await session.commit()

    async def on_submitted(remote_task_id: str) -> None:
        jobs[job_key] = {
            "asset_id": str(asset_id),
            "remote_task_id": remote_task_id,
        }
        _mark_request_data_dirty(task)
        await session.commit()

    return asset_id, resume, on_submitted
