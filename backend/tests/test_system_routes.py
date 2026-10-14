import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_matches_contract() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["code"] == "OK"
    assert response.json()["data"] == {"status": "ok"}
    assert response.json()["request_id"] == response.headers["x-request-id"]


@pytest.mark.asyncio
async def test_version_matches_contract() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/version")

    assert response.status_code == 200
    assert response.json()["code"] == "OK"
    assert response.json()["data"] == {"version": "0.1.0"}


@pytest.mark.asyncio
async def test_model_config_requires_login() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/model-config")

    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_REQUIRED"
    assert response.json()["data"] is None
