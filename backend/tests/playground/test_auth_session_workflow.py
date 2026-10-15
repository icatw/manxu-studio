from collections.abc import Awaitable, Callable
from typing import Any

import httpx
import pytest

from tests.playground.conftest import unwrap

pytestmark = pytest.mark.playground


@pytest.mark.asyncio
async def test_email_login_csrf_write_and_logout(
    api_client: httpx.AsyncClient,
    login_account: Callable[[str], Awaitable[dict[str, Any]]],
    unique_email: Callable[[], str],
) -> None:
    email = unique_email()
    account = await login_account(email)
    assert account["id"]

    me = await api_client.get("/auth/me")
    assert me.status_code == 200
    assert unwrap(me.json())["id"] == account["id"]

    # CSRF required for mutations.
    bare = httpx.AsyncClient(
        base_url=str(api_client.base_url),
        cookies=api_client.cookies,
        timeout=30.0,
        trust_env=False,
    )
    async with bare:
        denied = await bare.patch("/auth/me", json={"display_name": "NoCsrf"})
        assert denied.status_code in {403, 401}

    updated = await api_client.patch("/auth/me", json={"display_name": "Playground User"})
    assert updated.status_code == 200
    assert unwrap(updated.json())["display_name"] == "Playground User"

    logout = await api_client.post("/auth/logout")
    assert logout.status_code in {200, 204}

    after = await api_client.get("/auth/me")
    assert after.status_code == 401
