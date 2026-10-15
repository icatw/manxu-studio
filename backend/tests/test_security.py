import pytest
from fastapi import HTTPException

from app.core import security
from app.core.api_responses import ApiError


def test_model_secret_encryption_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        security, "get_settings", lambda: type("S", (), {"model_encryption_key": "x" * 48})()
    )
    encrypted = security.encrypt_secret("sample-secret")

    assert encrypted != b"sample-secret"
    assert security.decrypt_secret(encrypted) == "sample-secret"


def test_model_secret_encryption_reports_missing_master_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        security, "get_settings", lambda: type("S", (), {"model_encryption_key": ""})()
    )

    with pytest.raises(ApiError, match="模型密钥加密主密钥") as error:
        security.encrypt_secret("sample-secret")

    assert error.value.code == "SERVICE_UNAVAILABLE"
    assert error.value.status_code == 503


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    [
        "http://example.com/v1",
        "https://localhost/v1",
        "https://127.0.0.1/v1",
        "https://metadata.google.internal/",
        "https://user:pass@example.com/v1",
    ],
)
async def test_private_or_insecure_text_endpoints_are_rejected(url: str) -> None:
    with pytest.raises(HTTPException):
        await security.validate_public_https_url(url)


@pytest.mark.asyncio
async def test_private_model_base_urls_allowed_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        security,
        "get_settings",
        lambda: type("S", (), {"allow_private_model_base_urls": True})(),
    )
    await security.validate_public_https_url("http://fake-llm:8080/v1")
    with pytest.raises(HTTPException):
        await security.validate_public_https_url("https://metadata.google.internal/")
    with pytest.raises(HTTPException):
        await security.validate_public_https_url("ftp://fake-llm/v1")
