import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select

from app.core.logging import api_logger
from app.db.models import GenerationTaskRecord, ProjectRecord
from app.db.session import SessionFactory, engine
from app.tasks.registry import get_handler
from app.tasks.types import failure_for


def _problem(*, title: str, status: int, detail: str, code: str | None = None) -> dict[str, object]:
    problem: dict[str, object] = {
        "title": title,
        "status": status,
        "detail": detail,
    }
    if code:
        problem["code"] = code
    return problem


async def _mark_interrupted(task_id: UUID) -> None:
    """Return timed-out/cancelled work to queued so reclaim can pick it up promptly."""
    async with SessionFactory() as session:
        task = await session.get(GenerationTaskRecord, task_id)
        if task is None or task.status != "running":
            return
        task.status = "queued"
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
