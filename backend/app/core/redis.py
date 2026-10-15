from collections.abc import AsyncIterator, Awaitable
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import cast

from fastapi import HTTPException, Request
from redis.asyncio import Redis

from app.core.config import get_settings


@lru_cache
def get_redis_client() -> Redis:
    return cast(Redis, Redis.from_url(get_settings().redis_url, decode_responses=True))


@asynccontextmanager
async def redis_connection() -> AsyncIterator[Redis]:
    yield get_redis_client()


async def close_redis_client() -> None:
    if get_redis_client.cache_info().currsize:
        await get_redis_client().aclose()
        get_redis_client.cache_clear()


async def consume_rate_limit(key: str, limit: int, window_seconds: int = 60) -> bool:
    script = """
    local count = redis.call('INCR', KEYS[1])
    if count == 1 then
      redis.call('EXPIRE', KEYS[1], ARGV[1])
    end
    return count
    """
    async with redis_connection() as client:
        count = await cast(Awaitable[int], client.eval(script, 1, key, str(window_seconds)))
        return count <= limit


async def set_ephemeral_value(key: str, value: str, ttl_seconds: int) -> None:
    async with redis_connection() as client:
        await client.setex(key, ttl_seconds, value)


async def consume_ephemeral_value(key: str, expected: str) -> bool:
    script = """
    local current = redis.call('GET', KEYS[1])
    if current == ARGV[1] then
      return redis.call('DEL', KEYS[1])
    end
    return 0
    """
    async with redis_connection() as client:
        result = await cast(Awaitable[int], client.eval(script, 1, key, expected))
        return bool(result)


async def require_rate_limit(request: Request, limit: int | None = None) -> None:
    settings = get_settings()
    client_host = request.client.host if request.client else "unknown"
    account_id = getattr(request.state, "account_id", None)
    subject = f"account:{account_id}" if account_id else f"client:{client_host}"
    is_read = request.method.upper() in {"GET", "HEAD", "OPTIONS"}
    effective_limit = limit or (
        settings.read_rate_limit_per_minute if is_read else settings.rate_limit_per_minute
    )
    key = f"rate:{subject}:{request.method.upper()}:{request.url.path}"
    try:
        allowed = await consume_rate_limit(key, effective_limit)
    except Exception as error:
        raise HTTPException(503, "请求服务暂时不可用，请稍后重试") from error
    if not allowed:
        raise HTTPException(429, "请求过于频繁，请稍后重试")
