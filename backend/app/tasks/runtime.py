import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm.attributes import flag_modified

from app.core.logging import api_logger
from app.db.models import GenerationTaskRecord, ProjectRecord
from app.db.session import SessionFactory, engine
from app.providers.errors import AmbiguousProviderSubmitError, RecoverableProviderError
from app.tasks.registry import get_handler
from app.tasks.types import failure_for

# Cap automatic reclaim loops for transient provider failures.
MAX_RECOVERY_ATTEMPTS = 5
RECOVERY_ATTEMPTS_KEY = "recovery_attempts"


def _problem(*, title: str, status: int, detail: str, code: str | None = None) -> dict[str, object]:
    problem: dict[str, object] = {
        "title": title,
        "status": status,
        "detail": detail,
    }
    if code:
        problem["code"] = code
    return problem


def _request_data(task: GenerationTaskRecord) -> dict[str, Any]:
    raw = getattr(task, "request_data", None)
    if isinstance(raw, dict):
        return raw
    empty: dict[str, Any] = {}
    task.request_data = empty
    return empty


async def _mark_interrupted(task_id: UUID) -> None:
    """Return timed-out/cancelled work to queued so reclaim can pick it up promptly."""
    async with SessionFactory() as session:
        task = await session.get(GenerationTaskRecord, task_id)
        if task is None or task.status != "running":
            return
        task.status = "queued"
        task.updated_at = datetime.now(UTC)
        await session.commit()


async def _mark_recoverable(task_id: UUID, detail: str) -> None:
    """Requeue while under the recovery cap; otherwise fail visibly."""
    async with SessionFactory() as session:
        task = await session.get(GenerationTaskRecord, task_id)
        if task is None or task.status != "running":
            return
        request_data = _request_data(task)
        attempts = int(request_data.get(RECOVERY_ATTEMPTS_KEY, 0) or 0) + 1
        request_data[RECOVERY_ATTEMPTS_KEY] = attempts
        try:
            flag_modified(task, "request_data")
        except Exception:
            pass
        task.updated_at = datetime.now(UTC)
        if attempts > MAX_RECOVERY_ATTEMPTS:
            task.status = "failed"
            task.error = _problem(
                title="生成任务恢复次数过多",
                status=503,
                detail=detail,
                code="RECOVERY_EXHAUSTED",
            )
            api_logger.warning(
                "generation_task_recovery_exhausted",
                extra={
                    "event": "generation_task_recovery_exhausted",
                    "task_id": str(task_id),
                    "attempts": attempts,
                },
            )
        else:
            task.status = "queued"
            # Keep last recoverable detail visible while waiting for reclaim.
            task.error = _problem(
                title="生成任务等待恢复",
                status=503,
                detail=detail,
                code="RECOVERING",
            )
        await session.commit()


async def _mark_ambiguous_submit(task_id: UUID, detail: str) -> None:
    """Fail without auto-resubmit when a remote job may already exist."""
    async with SessionFactory() as session:
        task = await session.get(GenerationTaskRecord, task_id)
        if task is None or task.status != "running":
            return
        task.status = "failed"
        task.error = _problem(
            title="图像提交结果不确定",
            status=502,
            detail=detail,
            code="PROVIDER_SUBMIT_AMBIGUOUS",
        )
        task.updated_at = datetime.now(UTC)
        await session.commit()


async def run_generation_task(task_id: UUID) -> None:
    lock_id = int.from_bytes(task_id.bytes[:8], byteorder="big", signed=True)
    async with engine.connect() as lock_connection:
        acquired = await lock_connection.scalar(select(func.pg_try_advisory_lock(lock_id)))
        if not acquired:
            return
        task_type = "unknown"
        try:
            async with SessionFactory() as session:
                task = await session.get(GenerationTaskRecord, task_id)
                if task is None or task.status in {"succeeded", "failed"}:
                    return
                task_type = task.task_type
                project = await session.get(ProjectRecord, task.project_id)
                if project is None or project.owner_id != task.owner_id:
                    task.status = "failed"
                    task.error = _problem(
                        title="生成任务失败",
                        status=404,
                        detail="项目归属已变化",
                        code="NOT_FOUND",
                    )
                    task.updated_at = datetime.now(UTC)
                    await session.commit()
                    return
                task.status = "running"
                # Preserve progress across worker timeouts / requeues.
                if task.progress is None or task.progress < 5:
                    task.progress = 5
                task.updated_at = datetime.now(UTC)
                await session.commit()

            try:
                async with SessionFactory() as session:
                    task = await session.get(GenerationTaskRecord, task_id)
                    if task is None or task.status != "running":
                        return
                    handler = get_handler(task.task_type)
                    result = await handler(session, task)
                    task = await session.get(GenerationTaskRecord, task_id)
                    if task is None:
                        return
                    task.status = "succeeded"
                    task.progress = 100
                    task.result = result
                    task.error = None
                    request_data = _request_data(task)
                    request_data.pop(RECOVERY_ATTEMPTS_KEY, None)
                    try:
                        flag_modified(task, "request_data")
                    except Exception:
                        pass
                    task.updated_at = datetime.now(UTC)
                    await session.commit()
            except asyncio.CancelledError:
                api_logger.warning(
                    "generation_task_interrupted",
                    extra={
                        "event": "generation_task_interrupted",
                        "task_id": str(task_id),
                        "task_type": task_type,
                    },
                )
                await _mark_interrupted(task_id)
                raise
            except RecoverableProviderError as error:
                api_logger.warning(
                    "generation_task_recoverable",
                    extra={
                        "event": "generation_task_recoverable",
                        "task_id": str(task_id),
                        "task_type": task_type,
                        "error_type": type(error).__name__,
                    },
                )
                await _mark_recoverable(task_id, str(error) or "供应商暂时不可用")
                return
            except AmbiguousProviderSubmitError as error:
                api_logger.warning(
                    "generation_task_ambiguous_submit",
                    extra={
                        "event": "generation_task_ambiguous_submit",
                        "task_id": str(task_id),
                        "task_type": task_type,
                        "error_type": type(error).__name__,
                    },
                )
                await _mark_ambiguous_submit(task_id, str(error))
                return
            except Exception:
                failure_id = str(uuid4())
                api_logger.exception(
                    "generation_task_failed",
                    extra={
                        "event": "generation_task_failed",
                        "task_id": str(task_id),
                        "failure_id": failure_id,
                        "task_type": task_type,
                    },
                )
                failure = failure_for(task_type)
                async with SessionFactory() as session:
                    task = await session.get(GenerationTaskRecord, task_id)
                    if task is not None:
                        task.status = "failed"
                        problem = _problem(
                            title=failure["message"],
                            status=500,
                            detail=failure["message"],
                            code=failure["code"],
                        )
                        problem["failure_id"] = failure_id
                        task.error = problem
                        task.updated_at = datetime.now(UTC)
                        await session.commit()
        finally:
            await lock_connection.execute(select(func.pg_advisory_unlock(lock_id)))
