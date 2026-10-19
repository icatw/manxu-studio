"""OpenAI-compatible image provider (sync /images/generations)."""

from __future__ import annotations

import base64
from uuid import uuid4

import httpx
import pytest

from app.providers.openai_images import OpenAIImagesProvider


class _MemoryStore:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    async def put_bytes(self, key: str, content: bytes) -> str:
        self.objects[key] = content
        stem = key.rsplit(".", 1)[0]
        return f"/api/v1/assets/{stem}"

    async def get_bytes(self, key: str) -> bytes:
        return self.objects[key]

    def find_asset_key(self, asset_id: str) -> str | None:
        for key in self.objects:
            if key.startswith(asset_id):
                return key
        return None

    def read_asset_bytes(self, asset_id: str) -> bytes | None:
        key = self.find_asset_key(asset_id)
        return self.objects[key] if key else None

    def open_asset(self, asset_id: str) -> tuple[bytes, str] | None:
        raw = self.read_asset_bytes(asset_id)
        return (raw, "image/png") if raw else None

    async def open_asset_async(self, asset_id: str) -> tuple[bytes, str] | None:
        return self.open_asset(asset_id)


@pytest.mark.asyncio
async def test_openai_images_b64_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("ALL_PROXY", "all_proxy", "HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        monkeypatch.delenv(key, raising=False)
    store = _MemoryStore()
    provider = OpenAIImagesProvider(store=store)  # type: ignore[arg-type]
    png = base64.b64encode(b"fake-png-bytes").decode("ascii")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [{"b64_json": png, "url": None}]})

    transport = httpx.MockTransport(handler)
    original_init = httpx.AsyncClient.__init__

    def patched_init(self, *args, **kwargs):  # noqa: ANN001
        kwargs["transport"] = transport
        kwargs["proxy"] = None
        original_init(self, *args, **kwargs)

    async def _ok(_url: str) -> None:
        return None

    monkeypatch.setattr(httpx.AsyncClient, "__init__", patched_init)
    monkeypatch.setattr("app.providers.openai_images.validate_public_https_url", _ok)

    asset_id = uuid4()
    submitted: list[str] = []

    async def on_submitted(remote_id: str) -> None:
        submitted.append(remote_id)

    url = await provider.generate(
        api_key="test-key",
        model="agnes-image-2.5-flash",
        prompt="a quiet alley",
        asset_id=asset_id,
        base_url="https://apihub.agnes-ai.com/v1",
        on_submitted=on_submitted,
    )
    assert url == f"/api/v1/assets/{asset_id}"
    assert submitted == [f"openai-images:{asset_id}"]
    assert store.find_asset_key(str(asset_id)) is not None


@pytest.mark.asyncio
async def test_openai_images_resume_uses_existing_asset(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("ALL_PROXY", "all_proxy", "HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        monkeypatch.delenv(key, raising=False)
    store = _MemoryStore()
    asset_id = uuid4()
    store.objects[f"{asset_id}.png"] = b"already"
    provider = OpenAIImagesProvider(store=store)  # type: ignore[arg-type]

    async def _ok(_url: str) -> None:
        return None

    monkeypatch.setattr("app.providers.openai_images.validate_public_https_url", _ok)
    url = await provider.generate(
        api_key="test-key",
        model="agnes-image-2.5-flash",
        prompt="ignored",
        asset_id=asset_id,
        base_url="https://apihub.agnes-ai.com/v1",
        resume_task_id=f"openai-images:{asset_id}",
    )
    assert url == f"/api/v1/assets/{asset_id}"
