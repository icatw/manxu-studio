from __future__ import annotations

import asyncio
import os
import re
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

import httpx
import pytest

PLAYGROUND_BASE_URL = os.environ.get("PLAYGROUND_BASE_URL", "http://127.0.0.1:8001")
PLAYGROUND_MAILPIT_URL = os.environ.get("PLAYGROUND_MAILPIT_URL", "http://127.0.0.1:8026")
PLAYGROUND_FAKE_LLM_URL = os.environ.get("PLAYGROUND_FAKE_LLM_URL", "http://fake-llm:8080/v1")


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "playground: requires Docker playground stack")


@pytest.fixture(scope="session")
def playground_base_url() -> str:
    return PLAYGROUND_BASE_URL.rstrip("/")


@pytest.fixture(scope="session")
def mailpit_base_url() -> str:
    return PLAYGROUND_MAILPIT_URL.rstrip("/")


@pytest.fixture(scope="session")
def fake_llm_url() -> str:
    return PLAYGROUND_FAKE_LLM_URL.rstrip("/")


@pytest.fixture(scope="session", autouse=True)
def require_playground(playground_base_url: str) -> None:
    deadline = time.time() + 5
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            # trust_env=False avoids host SOCKS/HTTP proxies breaking local Compose.
            response = httpx.get(
                f"{playground_base_url}/api/v1/health",
                timeout=2.0,
                trust_env=False,
            )
            if response.status_code == 200:
                return
            last_error = RuntimeError(f"health status {response.status_code}")
        except Exception as error:  # noqa: BLE001
            last_error = error
        time.sleep(0.4)
    pytest.skip(f"Playground API unavailable at {playground_base_url}: {last_error}")


@pytest.fixture
def unique_email() -> Callable[[], str]:
    def _factory() -> str:
        return f"pg-{uuid.uuid4().hex[:12]}@manxu.dev"

    return _factory


def unwrap(payload: dict[str, Any]) -> Any:
    assert "data" in payload, payload
    return payload["data"]


async def wait_for_login_code(mailpit_base_url: str, email: str) -> str:
    normalized = email.strip().lower()
    deadline = time.time() + 30
    async with httpx.AsyncClient(timeout=5.0, trust_env=False) as client:
        while time.time() < deadline:
            response = await client.get(
                f"{mailpit_base_url}/api/v1/search",
                params={"query": f"to:{normalized}"},
            )
            response.raise_for_status()
            messages = response.json().get("messages") or []
            candidates = sorted(
                messages,
                key=lambda item: item.get("Created", ""),
                reverse=True,
            )
            for summary in candidates:
                detail = await client.get(f"{mailpit_base_url}/api/v1/message/{summary['ID']}")
                if detail.status_code != 200:
                    continue
                payload = detail.json()
                body = f"{payload.get('Text', '')}\n{payload.get('HTML', '')}"
                match = re.search(r"验证码是\s*(\d{6})", body)
                if match:
                    return match.group(1)
            await asyncio.sleep(0.4)
    raise TimeoutError(f"Timed out waiting for login code for {normalized}")


@pytest.fixture
async def api_client(playground_base_url: str) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        base_url=f"{playground_base_url}/api/v1",
        timeout=60.0,
        follow_redirects=False,
        trust_env=False,
    ) as client:
        yield client


@pytest.fixture
def login_account(
    api_client: httpx.AsyncClient,
    mailpit_base_url: str,
) -> Callable[[str], Awaitable[dict[str, Any]]]:
    async def _login(email: str) -> dict[str, Any]:
        code_response = await api_client.post("/auth/email/code", json={"email": email})
        assert code_response.status_code == 202, code_response.text
        code = await wait_for_login_code(mailpit_base_url, email)
        verify = await api_client.post(
            "/auth/email/verify",
            json={"email": email, "code": code},
        )
        assert verify.status_code == 200, verify.text
        csrf = await api_client.get("/auth/csrf")
        assert csrf.status_code == 200, csrf.text
        token = unwrap(csrf.json())["token"]
        api_client.headers["X-CSRF-Token"] = token
        return unwrap(verify.json())

    return _login
