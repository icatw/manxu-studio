from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.providers import local_store, qwen_image


class FakeResponse:
    def __init__(
        self,
        *,
        body: dict[str, object] | None = None,
        content: bytes = b"image-bytes",
        headers: dict[str, str] | None = None,
    ) -> None:
        self._body = body or {}
        self.content = content
        self.headers = headers or {"content-type": "image/png"}
        self.status_code = 200
        self.is_success = True

    def json(self) -> dict[str, object]:
        return self._body


class FakeClient:
    def __init__(self, **_: object) -> None:
        self.get_count = 0
        self.submitted: dict[str, object] | None = None

    async def __aenter__(self) -> "FakeClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def post(self, url: str, **kwargs: object) -> FakeResponse:
        self.submitted = {"url": url, **kwargs}
        return FakeResponse(body={"output": {"task_id": "task-1"}})

    async def get(self, url: str, **_: object) -> FakeResponse:
        self.get_count += 1
        if "/tasks/" in url:
            return FakeResponse(
                body={
                    "output": {
                        "task_status": "SUCCEEDED",
                        "choices": [
                            {
                                "message": {
                                    "content": [{"image": "https://images.example.com/result.png"}]
                                }
                            }
                        ],
                    }
                }
            )
        return FakeResponse()


@pytest.mark.asyncio
async def test_qwen_image_async_task_is_downloaded_to_persistent_storage(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    client = FakeClient()
    settings = SimpleNamespace(
        qwen_image_base_url="https://workspace.example.com/compatible-mode/v1",
        image_storage_dir=str(tmp_path),
    )
    monkeypatch.setattr(qwen_image.httpx, "AsyncClient", lambda **kwargs: client)
    monkeypatch.setattr(qwen_image.asyncio, "sleep", lambda _: _no_sleep())
    monkeypatch.setattr(qwen_image, "validate_public_https_url", _skip_url_validation)
    monkeypatch.setattr(qwen_image, "get_settings", lambda: settings)
    monkeypatch.setattr(local_store, "get_settings", lambda: settings)
    asset_id = uuid4()

    result = await qwen_image.generate_qwen_image(
        api_key="private", model="qwen-image-3.0-pro", prompt="comic panel", asset_id=asset_id
    )

    assert result == f"/api/v1/assets/{asset_id}"
    assert (tmp_path / f"{asset_id}.png").read_bytes() == b"image-bytes"
    assert client.submitted is not None
    assert client.submitted["url"] == (
        "https://workspace.example.com/api/v1/services/aigc/image-generation/generation"
    )
    request_headers = client.submitted["headers"]
    assert isinstance(request_headers, dict)
    assert request_headers["X-DashScope-Async"] == "enable"
    request_body = client.submitted["json"]
    assert isinstance(request_body, dict)
    assert request_body["input"] == {
        "messages": [{"role": "user", "content": [{"text": "comic panel"}]}]
    }


async def _no_sleep() -> None:
    return None


async def _skip_url_validation(_: str) -> None:
    return None
