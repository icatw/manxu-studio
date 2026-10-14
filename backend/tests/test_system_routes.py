import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.routes import system
from app.core.config import Settings


@pytest.mark.asyncio
async def test_health_matches_contract() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_version_matches_contract() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/version")

    assert response.status_code == 200
    assert response.json() == {"version": "0.1.0"}


@pytest.mark.asyncio
async def test_model_config_exposes_settings_without_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        system,
        "get_settings",
        lambda: Settings(
            text_model_provider="deepseek",
            text_model_id="deepseek-chat",
            text_model_api_key="private-token",
            image_model_provider="wanx",
            image_model_id="wan2.2-t2i-flash",
        ),
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/model-config")

    assert response.status_code == 200
    assert response.json()["text_model"] == "deepseek-chat"
    assert response.json()["text_api_key_configured"] is True
    assert response.json()["text_status"] == "not_connected"
    assert "private-token" not in response.text
    assert "text_model_api_key" not in response.json()
