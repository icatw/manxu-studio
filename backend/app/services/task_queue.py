from uuid import UUID

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from arq.constants import in_progress_key_prefix, job_key_prefix, result_key_prefix

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


def primary_generation_job_id(task_id: UUID) -> str:
    """Stable ID so cron cannot pile duplicate jobs for the same queued task."""
    return f"generation:{task_id}"


async def enqueue_generation_task(task_id: UUID, *, reclaim_if_blocked: bool = False) -> bool:
    """Enqueue a generation job with ARQ-native dedupe.

    Normal enqueue uses a stable job id. When that slot is blocked:
    - job still queued / in progress → do nothing (no duplicate flood)
    - leftover result key after timeout/finish → delete result and re-enqueue primary
    """
    pool = await get_arq_pool()
    primary_id = primary_generation_job_id(task_id)
    job = await pool.enqueue_job(
        "run_queued_generation_task",
        str(task_id),
        _job_id=primary_id,
    )
    if job is not None:
        return True
    if not reclaim_if_blocked:
        api_logger.info(
            "generation_enqueue_deduped",
            extra={
                "event": "generation_enqueue_deduped",
                "task_id": str(task_id),
                "job_id": primary_id,
            },
        )
        return False

    job_key = job_key_prefix + primary_id
    result_key = result_key_prefix + primary_id
    in_progress_key = in_progress_key_prefix + primary_id
    if await pool.exists(job_key) or await pool.exists(in_progress_key):
        api_logger.info(
            "generation_requeue_skipped_inflight",
            extra={
                "event": "generation_requeue_skipped_inflight",
                "task_id": str(task_id),
                "job_id": primary_id,
            },
        )
        return False
    if await pool.exists(result_key):
        await pool.delete(result_key)
        job = await pool.enqueue_job(
            "run_queued_generation_task",
            str(task_id),
            _job_id=primary_id,
        )
        if job is None:
            api_logger.warning(
                "generation_requeue_rejected",
                extra={
                    "event": "generation_requeue_rejected",
                    "task_id": str(task_id),
                    "job_id": primary_id,
                },
            )
            return False
        api_logger.info(
            "generation_requeued_after_result",
            extra={
                "event": "generation_requeued_after_result",
                "task_id": str(task_id),
                "job_id": primary_id,
            },
        )
        return True
    return False
