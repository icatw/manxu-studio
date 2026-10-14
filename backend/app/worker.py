from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

from arq import cron
from arq.connections import ArqRedis, RedisSettings
from sqlalchemy import or_, select

from app.db.models import GenerationTaskRecord
from app.db.session import SessionFactory
from app.services.task_queue import redis_settings
from app.services.workspace_tasks import run_generation_task


async def run_queued_generation_task(ctx: dict[str, object], task_id: str) -> None:
    await run_generation_task(UUID(task_id))


async def requeue_pending_generation_tasks(ctx: dict[str, object]) -> None:
    async with SessionFactory() as session:
        task_ids = await session.scalars(
            select(GenerationTaskRecord.id).where(
                or_(
                    GenerationTaskRecord.status == "queued",
                    (GenerationTaskRecord.status == "running")
                    & (GenerationTaskRecord.updated_at < datetime.now(UTC) - timedelta(minutes=5)),
                )
            )
        )
        redis = cast(ArqRedis, ctx["redis"])
        for task_id in task_ids:
            await redis.enqueue_job(
                "run_queued_generation_task",
                str(task_id),
                _job_id=f"generation:{task_id}",
            )


class WorkerSettings:
    functions = [run_queued_generation_task]
    on_startup = requeue_pending_generation_tasks
    cron_jobs = [cron(requeue_pending_generation_tasks, second={0}, run_at_startup=True)]
    redis_settings: RedisSettings = redis_settings()
    max_jobs = 2
    health_check_interval = 30
