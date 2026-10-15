from datetime import UTC, datetime, timedelta
from uuid import UUID

from arq import cron
from arq.connections import RedisSettings
from sqlalchemy import or_, select

from app.core.config import get_settings
from app.db.models import GenerationTaskRecord
from app.db.session import SessionFactory
from app.services.task_queue import enqueue_generation_task, redis_settings
from app.tasks import run_generation_task


async def run_queued_generation_task(ctx: dict[str, object], task_id: str) -> None:
    await run_generation_task(UUID(task_id))


async def requeue_pending_generation_tasks(ctx: dict[str, object]) -> None:
    """Reclaim lost work without flooding Redis with duplicate queued jobs.

    Healthy ``queued`` tasks share a stable primary job id (ARQ dedupes).
    Reclaim only clears a leftover result key and reuses that same id — never
    appends a fresh random job while the primary slot is still in flight.
    """
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
    for task_id in task_ids:
        await enqueue_generation_task(task_id, reclaim_if_blocked=True)


class WorkerSettings:
    functions = [run_queued_generation_task]
    on_startup = requeue_pending_generation_tasks
    cron_jobs = [cron(requeue_pending_generation_tasks, second={0}, run_at_startup=True)]
    redis_settings: RedisSettings = redis_settings()
    max_jobs = max(1, get_settings().image_model_concurrency)
    job_timeout = 900
    keep_result = 60
    health_check_interval = 30
