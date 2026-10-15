from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

from arq import cron
from arq.connections import ArqRedis, RedisSettings
from sqlalchemy import or_, select

from app.core.config import get_settings
from app.core.logging import api_logger
from app.db.models import GenerationTaskRecord
from app.db.session import SessionFactory
from app.services.task_queue import generation_job_id, redis_settings
from app.tasks import run_generation_task


async def run_queued_generation_task(ctx: dict[str, object], task_id: str) -> None:
    await run_generation_task(UUID(task_id))


async def requeue_pending_generation_tasks(ctx: dict[str, object]) -> None:
    async with SessionFactory() as session:
        task_ids = list(
            await session.scalars(
                select(GenerationTaskRecord.id).where(
                    or_(
                        GenerationTaskRecord.status == "queued",
                        (GenerationTaskRecord.status == "running")
                        & (
                            GenerationTaskRecord.updated_at
                            < datetime.now(UTC) - timedelta(minutes=15)
                        ),
                    )
                )
            )
        )
        redis = cast(ArqRedis, ctx["redis"])
        for task_id in task_ids:
            job_id = generation_job_id(task_id)
            job = await redis.enqueue_job(
                "run_queued_generation_task",
                str(task_id),
                _job_id=job_id,
            )
            if job is None:
                api_logger.warning(
                    "generation_requeue_rejected",
                    extra={
                        "event": "generation_requeue_rejected",
                        "task_id": str(task_id),
                        "job_id": job_id,
                    },
                )


class WorkerSettings:
    functions = [run_queued_generation_task]
    on_startup = requeue_pending_generation_tasks
    cron_jobs = [cron(requeue_pending_generation_tasks, second={0}, run_at_startup=True)]
    redis_settings: RedisSettings = redis_settings()
    max_jobs = max(1, get_settings().image_model_concurrency)
    job_timeout = 900
    # Timed-out jobs still write a result key; keep it briefly so unique job IDs reclaim fast.
    keep_result = 60
    health_check_interval = 30
