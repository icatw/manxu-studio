from uuid import UUID

from arq import create_pool
from arq.connections import RedisSettings

from app.core.config import get_settings


def redis_settings() -> RedisSettings:
    settings = get_settings()
    return RedisSettings.from_dsn(settings.redis_url)


async def enqueue_generation_task(task_id: UUID) -> None:
    pool = await create_pool(redis_settings())
    try:
        await pool.enqueue_job(
            "run_queued_generation_task", str(task_id), _job_id=f"generation:{task_id}"
        )
    finally:
        await pool.close()
