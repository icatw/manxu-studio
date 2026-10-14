import pytest
from fastapi import HTTPException

from app.core import security


def test_model_secret_encryption_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        security, "get_settings", lambda: type("S", (), {"model_encryption_key": "x" * 48})()
    )
    encrypted = security.encrypt_secret("sample-secret")

    assert encrypted != b"sample-secret"
    assert security.decrypt_secret(encrypted) == "sample-secret"


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
