"""Generation task and export application service."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from urllib.parse import quote
from uuid import UUID

from fastapi import HTTPException
from fastapi.responses import FileResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.config import get_settings
from app.db.models import EpisodeRecord, ExportRecord, GenerationTaskRecord
from app.schemas.workspace import (
    ExportRequest,
    GenerationProviderResumeRequest,
    GenerationTask,
)
from app.services.task_queue import enqueue_generation_task
from app.tasks.checkpoints import strip_resumable_checkpoints
from app.tasks.retry_policy import (
    PROVIDER_PROTECTED_ERROR_CODES,
    authorize_provider_resubmit,
    bind_remote_task_id,
    blocks_ordinary_retry,
    has_provider_resume_checkpoint,
    has_saved_remote_task_id,
    requires_resubmit_acknowledgment,
    task_error_code,
)
from app.tasks.runtime import RECOVERY_ATTEMPTS_KEY

_IDEMPOTENT_REUSE_STATUSES = frozenset({"queued", "running", "succeeded"})
_IDEMPOTENT_RELEASE_STATUSES = frozenset({"failed"})


def not_found(resource: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{resource}不存在")


def task_view(task: GenerationTaskRecord) -> GenerationTask:
    return GenerationTask.model_validate(task)


async def create_task(
    session: AsyncSession,
    *,
    owner_id: UUID,
    project_id: UUID,
    task_type: str,
    request_data: dict[str, object],
    episode_id: UUID | None = None,
    panel_id: UUID | None = None,
    retry_of_task_id: UUID | None = None,
    idempotency_key: str | None = None,
) -> GenerationTask:
    if idempotency_key:
        existing = await session.scalar(
            select(GenerationTaskRecord).where(
                GenerationTaskRecord.owner_id == owner_id,
                GenerationTaskRecord.idempotency_key == idempotency_key,
            )
        )
        if existing is not None:
            if existing.status in _IDEMPOTENT_REUSE_STATUSES:
                return task_view(existing)
            if existing.status in _IDEMPOTENT_RELEASE_STATUSES:
                existing.idempotency_key = None
                await session.flush()
            else:
                return task_view(existing)
    task = GenerationTaskRecord(
        owner_id=owner_id,
        project_id=project_id,
        episode_id=episode_id,
        panel_id=panel_id,
        task_type=task_type,
        status="queued",
        progress=0,
        request_data=request_data,
        retry_of_task_id=retry_of_task_id,
        idempotency_key=idempotency_key,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    try:
        await enqueue_generation_task(task.id, reclaim_if_blocked=False)
    except Exception as error:
        raise HTTPException(503, "生成队列暂时不可用，任务已保存并将在服务恢复后重试") from error
    return task_view(task)


async def get_task(session: AsyncSession, task_id: UUID) -> GenerationTask:
    task = await session.get(GenerationTaskRecord, task_id)
    if task is None:
        raise not_found("生成任务")
    return task_view(task)


_ACTIVE_TASK_STATUSES = ("queued", "running")


async def list_episode_tasks(
    session: AsyncSession, *, episode_id: UUID, active_only: bool = True
) -> list[GenerationTask]:
    episode = await session.get(EpisodeRecord, episode_id)
    if episode is None:
        raise not_found("故事单元")
    stmt = (
        select(GenerationTaskRecord)
        .where(GenerationTaskRecord.episode_id == episode_id)
        .order_by(GenerationTaskRecord.created_at.desc())
    )
    if active_only:
        stmt = stmt.where(GenerationTaskRecord.status.in_(_ACTIVE_TASK_STATUSES))
    rows = await session.scalars(stmt)
    return [task_view(row) for row in rows]


async def retry_task(session: AsyncSession, *, task_id: UUID, owner_id: UUID) -> GenerationTask:
    previous = await session.get(GenerationTaskRecord, task_id)
    if previous is None:
        raise not_found("生成任务")
    if previous.status != "failed":
        raise HTTPException(status_code=409, detail="只有失败的任务可以重试")
    if blocks_ordinary_retry(previous.error, previous.request_data):
        code = task_error_code(previous.error) or "unknown"
        raise HTTPException(
            status_code=409,
            detail=(
                f"失败码 {code} 可能已创建远端图像任务，禁止清除检查点的普通重试；"
                "请使用供应商续跑接口绑定远端任务或显式确认重新提交"
            ),
        )
    return await create_task(
        session,
        owner_id=owner_id,
        project_id=previous.project_id,
        episode_id=previous.episode_id,
        panel_id=previous.panel_id,
        task_type=previous.task_type,
        request_data=strip_resumable_checkpoints(previous.request_data),
        retry_of_task_id=previous.id,
    )


async def resume_provider_task(
    session: AsyncSession, *, task_id: UUID, body: GenerationProviderResumeRequest
) -> GenerationTask:
    task = await session.get(GenerationTaskRecord, task_id)
    if task is None:
        raise not_found("生成任务")
    if task.status != "failed":
        raise HTTPException(status_code=409, detail="只有失败的任务可以续跑")
    request_data = task.request_data if isinstance(task.request_data, dict) else {}
    if not isinstance(task.request_data, dict):
        task.request_data = request_data
    code = task_error_code(task.error)
    if code not in PROVIDER_PROTECTED_ERROR_CODES and not has_provider_resume_checkpoint(
        request_data
    ):
        raise HTTPException(
            status_code=409,
            detail="当前失败不需要供应商续跑，请使用普通重试",
        )

    remote_task_id = (body.remote_task_id or "").strip() or None
    needs_ack = requires_resubmit_acknowledgment(request_data) or (
        code == "PROVIDER_SUBMIT_AMBIGUOUS" and not has_saved_remote_task_id(request_data)
    )
    if remote_task_id:
        try:
            bind_remote_task_id(
                cast(dict[str, Any], request_data),
                remote_task_id=remote_task_id,
                job_key=body.job_key,
            )
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
    elif needs_ack and not body.acknowledge_resubmit:
        raise HTTPException(
            status_code=409,
            detail=(
                "提交结果不确定：请提供已确认的 remote_task_id 以续跑，"
                "或设置 acknowledge_resubmit=true 接受可能的重复计费后重新提交"
            ),
        )
    elif needs_ack and body.acknowledge_resubmit:
        try:
            authorize_provider_resubmit(
                request_data,
                job_key=body.job_key,
                include_ready=code == "PROVIDER_SUBMIT_AMBIGUOUS",
            )
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    request_data[RECOVERY_ATTEMPTS_KEY] = 0
    try:
        flag_modified(task, "request_data")
    except Exception:
        pass
    task.status = "queued"
    task.error = None
    task.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(task)
    try:
        await enqueue_generation_task(task.id, reclaim_if_blocked=True)
    except Exception as error:
        raise HTTPException(503, "生成队列暂时不可用，任务已保存并将在服务恢复后重试") from error
    return task_view(task)


async def create_export(
    session: AsyncSession, *, episode_id: UUID, owner_id: UUID, body: ExportRequest
) -> GenerationTask:
    episode = await session.get(EpisodeRecord, episode_id)
    if episode is None:
        raise not_found("故事单元")
    return await create_task(
        session,
        owner_id=owner_id,
        project_id=episode.project_id,
        episode_id=episode.id,
        task_type="export",
        request_data={**body.model_dump(mode="json"), "episode_id": str(episode.id)},
    )


async def download_export(session: AsyncSession, asset_id: UUID) -> Response:
    record = await session.get(ExportRecord, asset_id)
    if record is None:
        raise not_found("导出文件")
    filename = Path(record.filename).name
    content_disposition = f"attachment; filename=export; filename*=UTF-8''{quote(filename)}"
    return Response(
        content=record.content,
        media_type=record.content_type,
        headers={"Content-Disposition": content_disposition},
    )


async def get_image_asset(asset_id: UUID) -> FileResponse:
    storage = await asyncio.to_thread(Path(get_settings().image_storage_dir).resolve)
    for suffix, media_type in (
        (".png", "image/png"),
        (".jpg", "image/jpeg"),
        (".webp", "image/webp"),
    ):
        path = storage / f"{asset_id}{suffix}"
        if await asyncio.to_thread(path.is_file):
            return FileResponse(
                path,
                media_type=media_type,
                filename=f"{asset_id}{suffix}",
                headers={"Cache-Control": "private, no-store"},
            )
    raise not_found("图片资源")
