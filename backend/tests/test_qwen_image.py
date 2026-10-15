from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest

from app.providers import local_store, qwen_image
from app.providers.errors import AmbiguousProviderSubmitError, RecoverableProviderError


class FakeResponse:
    def __init__(
        self,
        *,
        body: dict[str, object] | None = None,
        content: bytes = b"image-bytes",
        headers: dict[str, str] | None = None,
        status_code: int = 200,
    ) -> None:
        self._body = body or {}
        self.content = content
        self.headers = headers or {"content-type": "image/png"}
        self.status_code = status_code
        self.is_success = 200 <= status_code < 300

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
        image_task_poll_interval_seconds=0,
        image_task_poll_max_attempts=5,
    )
    monkeypatch.setattr(qwen_image.httpx, "AsyncClient", lambda **kwargs: client)
    monkeypatch.setattr(qwen_image.asyncio, "sleep", lambda _: _no_sleep())
    monkeypatch.setattr(qwen_image, "validate_public_https_url", _skip_url_validation)
    monkeypatch.setattr(qwen_image, "get_settings", lambda: settings)
    monkeypatch.setattr(local_store, "get_settings", lambda: settings)
    asset_id = uuid4()
    events: list[str] = []

    async def on_submit_started() -> None:
        events.append("started")

    async def on_submitted(task_id: str) -> None:
        assert task_id == "task-1"
        events.append("submitted")

    result = await qwen_image.generate_qwen_image(
        api_key="private",
        model="qwen-image-3.0-pro",
        prompt="comic panel",
        asset_id=asset_id,
        on_submit_started=on_submit_started,
        on_submitted=on_submitted,
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
    assert events == ["started", "submitted"]


@pytest.mark.asyncio
async def test_qwen_image_resume_skips_resubmit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    client = FakeClient()
    settings = SimpleNamespace(
        qwen_image_base_url="https://dashscope.aliyuncs.com/api/v1",
        image_storage_dir=str(tmp_path),
        image_task_poll_interval_seconds=0,
        image_task_poll_max_attempts=5,
    )
    submitted: list[str] = []

    async def on_submitted(task_id: str) -> None:
        submitted.append(task_id)

    monkeypatch.setattr(qwen_image.httpx, "AsyncClient", lambda **kwargs: client)
    monkeypatch.setattr(qwen_image.asyncio, "sleep", lambda _: _no_sleep())
    monkeypatch.setattr(qwen_image, "validate_public_https_url", _skip_url_validation)
    monkeypatch.setattr(qwen_image, "get_settings", lambda: settings)
    monkeypatch.setattr(local_store, "get_settings", lambda: settings)

    asset_id = uuid4()
    result = await qwen_image.generate_image(
        api_key="private",
        model="qwen-image-3.0-pro",
        prompt="resume",
        asset_id=asset_id,
        resume_task_id="existing-remote-task",
        on_submitted=on_submitted,
    )

    assert result == f"/api/v1/assets/{asset_id}"
    assert client.submitted is None
    assert submitted == []
    assert client.get_count >= 1


@pytest.mark.asyncio
async def test_qwen_image_resume_resubmits_when_remote_already_failed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class FailedThenOkClient(FakeClient):
        async def get(self, url: str, **_: object) -> FakeResponse:
            self.get_count += 1
            if self.get_count == 1:
                return FakeResponse(body={"output": {"task_status": "FAILED"}})
            return await super().get(url)

    client = FailedThenOkClient()
    settings = SimpleNamespace(
        qwen_image_base_url="https://dashscope.aliyuncs.com/api/v1",
        image_storage_dir=str(tmp_path),
        image_task_poll_interval_seconds=0,
        image_task_poll_max_attempts=5,
    )
    submitted: list[str] = []

    async def on_submitted(task_id: str) -> None:
        submitted.append(task_id)

    monkeypatch.setattr(qwen_image.httpx, "AsyncClient", lambda **kwargs: client)
    monkeypatch.setattr(qwen_image.asyncio, "sleep", lambda _: _no_sleep())
    monkeypatch.setattr(qwen_image, "validate_public_https_url", _skip_url_validation)
    monkeypatch.setattr(qwen_image, "get_settings", lambda: settings)
    monkeypatch.setattr(local_store, "get_settings", lambda: settings)

    asset_id = uuid4()
    result = await qwen_image.generate_image(
        api_key="private",
        model="qwen-image-3.0-pro",
        prompt="retry",
        asset_id=asset_id,
        resume_task_id="dead-remote-task",
        on_submitted=on_submitted,
    )

    assert result == f"/api/v1/assets/{asset_id}"
    assert client.submitted is not None
    assert submitted == ["task-1"]


@pytest.mark.asyncio
async def test_qwen_image_resume_probe_429_does_not_resubmit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class RateLimitedProbeClient(FakeClient):
        async def get(self, url: str, **_: object) -> FakeResponse:
            self.get_count += 1
            if "/tasks/" in url:
                return FakeResponse(status_code=429, body={"message": "Too Many Requests"})
            return FakeResponse()

    client = RateLimitedProbeClient()
    settings = SimpleNamespace(
        qwen_image_base_url="https://dashscope.aliyuncs.com/api/v1",
        image_storage_dir=str(tmp_path),
        image_task_poll_interval_seconds=0,
        image_task_poll_max_attempts=5,
    )
    monkeypatch.setattr(qwen_image.httpx, "AsyncClient", lambda **kwargs: client)
    monkeypatch.setattr(qwen_image.asyncio, "sleep", lambda _: _no_sleep())
    monkeypatch.setattr(qwen_image, "validate_public_https_url", _skip_url_validation)
    monkeypatch.setattr(qwen_image, "get_settings", lambda: settings)
    monkeypatch.setattr(local_store, "get_settings", lambda: settings)

    with pytest.raises(RecoverableProviderError, match="查询 Qwen Image 任务失败"):
        await qwen_image.generate_image(
            api_key="private",
            model="qwen-image-3.0-pro",
            prompt="resume",
            asset_id=uuid4(),
            resume_task_id="existing-remote-task",
        )

    assert client.submitted is None


@pytest.mark.asyncio
async def test_qwen_image_resume_probe_5xx_does_not_resubmit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class ServerErrorProbeClient(FakeClient):
        async def get(self, url: str, **_: object) -> FakeResponse:
            self.get_count += 1
            if "/tasks/" in url:
                return FakeResponse(status_code=503, body={"message": "Unavailable"})
            return FakeResponse()

    client = ServerErrorProbeClient()
    settings = SimpleNamespace(
        qwen_image_base_url="https://dashscope.aliyuncs.com/api/v1",
        image_storage_dir=str(tmp_path),
        image_task_poll_interval_seconds=0,
        image_task_poll_max_attempts=5,
    )
    monkeypatch.setattr(qwen_image.httpx, "AsyncClient", lambda **kwargs: client)
    monkeypatch.setattr(qwen_image.asyncio, "sleep", lambda _: _no_sleep())
    monkeypatch.setattr(qwen_image, "validate_public_https_url", _skip_url_validation)
    monkeypatch.setattr(qwen_image, "get_settings", lambda: settings)
    monkeypatch.setattr(local_store, "get_settings", lambda: settings)

    with pytest.raises(RecoverableProviderError, match="查询 Qwen Image 任务失败"):
        await qwen_image.generate_image(
            api_key="private",
            model="qwen-image-3.0-pro",
            prompt="resume",
            asset_id=uuid4(),
            resume_task_id="existing-remote-task",
        )

    assert client.submitted is None


@pytest.mark.asyncio
async def test_qwen_image_submit_5xx_is_ambiguous_not_auto_retried(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class SubmitFailClient(FakeClient):
        async def post(self, url: str, **kwargs: object) -> FakeResponse:
            self.submitted = {"url": url, **kwargs}
            return FakeResponse(status_code=503, body={"message": "Unavailable"})

    client = SubmitFailClient()
    settings = SimpleNamespace(
        qwen_image_base_url="https://dashscope.aliyuncs.com/api/v1",
        image_storage_dir=str(tmp_path),
        image_task_poll_interval_seconds=0,
        image_task_poll_max_attempts=5,
    )
    monkeypatch.setattr(qwen_image.httpx, "AsyncClient", lambda **kwargs: client)
    monkeypatch.setattr(qwen_image, "validate_public_https_url", _skip_url_validation)
    monkeypatch.setattr(qwen_image, "get_settings", lambda: settings)
    monkeypatch.setattr(local_store, "get_settings", lambda: settings)

    with pytest.raises(AmbiguousProviderSubmitError, match="提交结果不确定"):
        await qwen_image.generate_image(
            api_key="private",
            model="qwen-image-3.0-pro",
            prompt="create",
            asset_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_qwen_image_submit_429_is_recoverable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class RateLimitedSubmitClient(FakeClient):
        async def post(self, url: str, **kwargs: object) -> FakeResponse:
            self.submitted = {"url": url, **kwargs}
            return FakeResponse(status_code=429, body={"message": "Too Many Requests"})

    client = RateLimitedSubmitClient()
    settings = SimpleNamespace(
        qwen_image_base_url="https://dashscope.aliyuncs.com/api/v1",
        image_storage_dir=str(tmp_path),
        image_task_poll_interval_seconds=0,
        image_task_poll_max_attempts=5,
    )
    monkeypatch.setattr(qwen_image.httpx, "AsyncClient", lambda **kwargs: client)
    monkeypatch.setattr(qwen_image, "validate_public_https_url", _skip_url_validation)
    monkeypatch.setattr(qwen_image, "get_settings", lambda: settings)
    monkeypatch.setattr(local_store, "get_settings", lambda: settings)
    events: list[str] = []

    async def on_submit_started() -> None:
        events.append("started")

    async def on_submit_rejected() -> None:
        events.append("rejected")

    with pytest.raises(RecoverableProviderError, match="提交限流"):
        await qwen_image.generate_image(
            api_key="private",
            model="qwen-image-3.0-pro",
            prompt="create",
            asset_id=uuid4(),
            on_submit_started=on_submit_started,
            on_submit_rejected=on_submit_rejected,
        )
    assert events == ["started", "rejected"]


@pytest.mark.asyncio
async def test_qwen_image_submit_checkpoint_failure_is_ambiguous(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    client = FakeClient()
    settings = SimpleNamespace(
        qwen_image_base_url="https://dashscope.aliyuncs.com/api/v1",
        image_storage_dir=str(tmp_path),
        image_task_poll_interval_seconds=0,
        image_task_poll_max_attempts=5,
    )
    monkeypatch.setattr(qwen_image.httpx, "AsyncClient", lambda **kwargs: client)
    monkeypatch.setattr(qwen_image, "validate_public_https_url", _skip_url_validation)
    monkeypatch.setattr(qwen_image, "get_settings", lambda: settings)
    monkeypatch.setattr(local_store, "get_settings", lambda: settings)

    async def failed_checkpoint(_task_id: str) -> None:
        raise RuntimeError("database commit failed")

    with pytest.raises(AmbiguousProviderSubmitError) as raised:
        await qwen_image.generate_image(
            api_key="private",
            model="qwen-image-3.0-pro",
            prompt="create",
            asset_id=uuid4(),
            on_submitted=failed_checkpoint,
        )

    assert raised.value.remote_task_id == "task-1"
    assert client.get_count == 0


@pytest.mark.asyncio
async def test_qwen_image_probe_network_error_keeps_existing_remote_job(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class ProbeTimeoutClient(FakeClient):
        async def get(self, url: str, **kwargs: object) -> FakeResponse:
            if "/tasks/" in url:
                raise httpx.ReadTimeout("timeout")
            return await super().get(url, **kwargs)

    client = ProbeTimeoutClient()
    settings = SimpleNamespace(
        qwen_image_base_url="https://dashscope.aliyuncs.com/api/v1",
        image_storage_dir=str(tmp_path),
        image_task_poll_interval_seconds=0,
        image_task_poll_max_attempts=5,
    )
    monkeypatch.setattr(qwen_image.httpx, "AsyncClient", lambda **kwargs: client)
    monkeypatch.setattr(qwen_image, "validate_public_https_url", _skip_url_validation)
    monkeypatch.setattr(qwen_image, "get_settings", lambda: settings)
    monkeypatch.setattr(local_store, "get_settings", lambda: settings)

    with pytest.raises(RecoverableProviderError, match="网络暂时不可用"):
        await qwen_image.generate_image(
            api_key="private",
            model="qwen-image-3.0-pro",
            prompt="resume",
            asset_id=uuid4(),
            resume_task_id="existing-remote-task",
        )

    assert client.submitted is None


@pytest.mark.asyncio
async def test_qwen_image_probe_401_is_permanent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class AuthFailProbeClient(FakeClient):
        async def get(self, url: str, **_: object) -> FakeResponse:
            self.get_count += 1
            if "/tasks/" in url:
                return FakeResponse(status_code=401, body={"message": "Unauthorized"})
            return FakeResponse()

    client = AuthFailProbeClient()
    settings = SimpleNamespace(
        qwen_image_base_url="https://dashscope.aliyuncs.com/api/v1",
        image_storage_dir=str(tmp_path),
        image_task_poll_interval_seconds=0,
        image_task_poll_max_attempts=5,
    )
    monkeypatch.setattr(qwen_image.httpx, "AsyncClient", lambda **kwargs: client)
    monkeypatch.setattr(qwen_image, "validate_public_https_url", _skip_url_validation)
    monkeypatch.setattr(qwen_image, "get_settings", lambda: settings)
    monkeypatch.setattr(local_store, "get_settings", lambda: settings)

    with pytest.raises(ValueError, match="请检查图像 API Key"):
        await qwen_image.generate_image(
            api_key="private",
            model="qwen-image-3.0-pro",
            prompt="resume",
            asset_id=uuid4(),
            resume_task_id="existing-remote-task",
        )

    assert client.submitted is None


async def _no_sleep() -> None:
    return None


async def _skip_url_validation(_: str) -> None:
    return None
