from uuid import UUID, uuid4

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.core.config import get_settings
from app.core.logging import api_logger

_pool: ArqRedis | None = None


def redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(get_settings().redis_url)


async def get_arq_pool() -> ArqRedis:
    global _pool
    if _pool is None:
        _pool = await create_pool(redis_settings())
    return _pool


async def close_arq_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def generation_job_id(task_id: UUID) -> str:
    """Unique per enqueue so ARQ result keys from timed-out jobs cannot block reclaim."""
    return f"generation:{task_id}:{uuid4().hex[:12]}"


async def enqueue_generation_task(task_id: UUID) -> None:
    pool = await get_arq_pool()
    job_id = generation_job_id(task_id)
    job = await pool.enqueue_job(
        "run_queued_generation_task",
        str(task_id),
        _job_id=job_id,
    )
    if job is None:
        api_logger.warning(
            "generation_enqueue_rejected",
            extra={
                "event": "generation_enqueue_rejected",
                "task_id": str(task_id),
                "job_id": job_id,
            },
        )
        raise RuntimeError("生成任务入队失败，请稍后重试")
