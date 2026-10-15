from types import SimpleNamespace

import pytest

from app.core import redis


@pytest.mark.asyncio
@pytest.mark.parametrize(("method", "expected_limit"), [("GET", 120), ("POST", 30)])
async def test_rate_limit_uses_method_policy_and_account_scope(
    monkeypatch: pytest.MonkeyPatch, method: str, expected_limit: int
) -> None:
    captured: dict[str, object] = {}

    async def consume(key: str, limit: int) -> bool:
        captured["key"] = key
        captured["limit"] = limit
        return True

    monkeypatch.setattr(
        redis,
        "get_settings",
        lambda: SimpleNamespace(rate_limit_per_minute=30, read_rate_limit_per_minute=120),
    )
    monkeypatch.setattr(redis, "consume_rate_limit", consume)
    request = SimpleNamespace(
        method=method,
        client=SimpleNamespace(host="proxy"),
        url=SimpleNamespace(path="/generation-tasks/task-id"),
        state=SimpleNamespace(account_id="account-id"),
    )

    await redis.require_rate_limit(request)  # type: ignore[arg-type]

    assert captured == {
        "key": f"rate:account:account-id:{method}:/generation-tasks/task-id",
        "limit": expected_limit,
    }
