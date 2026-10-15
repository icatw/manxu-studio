from collections.abc import Callable

import httpx
import pytest

from tests.playground.conftest import unwrap, wait_for_login_code

pytestmark = pytest.mark.playground


@pytest.mark.asyncio
async def test_other_account_cannot_access_project(
    playground_base_url: str,
    mailpit_base_url: str,
    unique_email: Callable[[], str],
) -> None:
    email_a = unique_email()
    email_b = unique_email()

    async with httpx.AsyncClient(
        base_url=f"{playground_base_url}/api/v1",
        timeout=60.0,
        trust_env=False,
    ) as client_a:
        code_a = await client_a.post("/auth/email/code", json={"email": email_a})
        assert code_a.status_code == 202
        verify_a = await client_a.post(
            "/auth/email/verify",
            json={"email": email_a, "code": await wait_for_login_code(mailpit_base_url, email_a)},
        )
        assert verify_a.status_code == 200
        csrf_a = unwrap((await client_a.get("/auth/csrf")).json())["token"]
        client_a.headers["X-CSRF-Token"] = csrf_a

        created = await client_a.post(
            "/projects",
            json={
                "title": "仅 A 可见",
                "synopsis": "跨账户隔离验证。",
                "genre": "都市",
                "art_style": "日系",
                "aspect_ratio": "portrait",
            },
        )
        assert created.status_code == 201, created.text
        project_id = unwrap(created.json())["id"]

    async with httpx.AsyncClient(
        base_url=f"{playground_base_url}/api/v1",
        timeout=60.0,
        trust_env=False,
    ) as client_b:
        code_b = await client_b.post("/auth/email/code", json={"email": email_b})
        assert code_b.status_code == 202
        verify_b = await client_b.post(
            "/auth/email/verify",
            json={"email": email_b, "code": await wait_for_login_code(mailpit_base_url, email_b)},
        )
        assert verify_b.status_code == 200
        csrf_b = unwrap((await client_b.get("/auth/csrf")).json())["token"]
        client_b.headers["X-CSRF-Token"] = csrf_b

        assert (await client_b.get(f"/projects/{project_id}")).status_code == 404
        assert (
            await client_b.patch(f"/projects/{project_id}", json={"title": "hijack"})
        ).status_code == 404
        assert (await client_b.delete(f"/projects/{project_id}")).status_code == 404
