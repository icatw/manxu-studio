import asyncio
from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

import httpx

from app.core.config import get_settings
from app.core.security import validate_public_https_url
from app.providers.errors import (
    AmbiguousProviderSubmitError,
    ProviderCheckpointError,
    RecoverableProviderError,
)
from app.providers.local_store import LocalObjectStore

OnSubmitted = Callable[[str], Awaitable[None]]
_TERMINAL_REMOTE = frozenset({"FAILED", "CANCELED", "UNKNOWN"})


def _raise_query_failure(status_code: int) -> None:
    message = f"查询 Qwen Image 任务失败（HTTP {status_code}）"
    if status_code in {401, 403}:
        raise ValueError(f"{message}，请检查图像 API Key")
    if status_code == 429 or status_code >= 500:
        raise RecoverableProviderError(message)
    # Other 4xx are permanent (bad request / not allowed), not auto-retried.
    raise ValueError(message)


def normalize_dashscope_api_base(configured_base_url: str) -> str:
    """Map Workspace OpenAI-compatible hosts to DashScope async Image API roots."""
    configured = urlsplit(configured_base_url)
    path = configured.path.rstrip("/")
    if path.endswith("/compatible-mode/v1"):
        path = path[: -len("/compatible-mode/v1")]
    if not path.endswith("/api/v1"):
        path = f"{path}/api/v1" if path else "/api/v1"
    return urlunsplit((configured.scheme, configured.netloc, path, "", "")).rstrip("/")


class QwenImageProvider:
    """DashScope async image generation with persistent local storage."""

    def __init__(self, store: LocalObjectStore | None = None) -> None:
        self._store = store or LocalObjectStore()

    async def generate(
        self,
        *,
        api_key: str,
        model: str,
        prompt: str,
        asset_id: UUID,
        base_url: str | None = None,
        resume_task_id: str | None = None,
        prompt_extend: bool = True,
        on_submit_started: Callable[[], Awaitable[None]] | None = None,
        on_submit_rejected: Callable[[], Awaitable[None]] | None = None,
        on_submitted: OnSubmitted | None = None,
    ) -> str:
        settings = get_settings()
        configured_base_url = base_url or settings.qwen_image_base_url
        await validate_public_https_url(configured_base_url)
        api_root = normalize_dashscope_api_base(configured_base_url)
        auth_headers = {"Authorization": f"Bearer {api_key}"}
        headers = {
            **auth_headers,
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
        }
        timeout = httpx.Timeout(45, connect=10)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            task_id = resume_task_id
            if task_id:
                try:
                    probe = await client.get(f"{api_root}/tasks/{task_id}", headers=auth_headers)
                except httpx.RequestError as error:
                    raise RecoverableProviderError(
                        "查询 Qwen Image 任务时网络暂时不可用"
                    ) from error
                if probe.is_success:
                    try:
                        probe_status = probe.json().get("output", {}).get("task_status")
                    except (ValueError, AttributeError) as error:
                        raise RecoverableProviderError(
                            "Qwen Image 任务状态响应暂时无法读取"
                        ) from error
                    if probe_status in _TERMINAL_REMOTE:
                        # Only terminal remote outcomes discard the checkpoint.
                        task_id = None
                elif probe.status_code == 404:
                    task_id = None
                else:
                    # Transient probe failures must not spawn a new billable job.
                    _raise_query_failure(probe.status_code)

            if not task_id:
                # DashScope has no idempotency key: each POST may create a billable job.
                # Only auto-retry submits that clearly were not accepted (e.g. 429).
                if on_submit_started is not None:
                    await on_submit_started()
                endpoint = f"{api_root}/services/aigc/image-generation/generation"
                payload = {
                    "model": model,
                    "input": {"messages": [{"role": "user", "content": [{"text": prompt}]}]},
                    "parameters": {"size": "1024*1024", "prompt_extend": prompt_extend},
                }
                try:
                    response = await client.post(endpoint, headers=headers, json=payload)
                except httpx.TimeoutException as error:
                    raise AmbiguousProviderSubmitError(
                        "Qwen Image 提交超时，远端可能已创建任务；请勿自动重提，避免重复计费"
                    ) from error
                except httpx.RequestError as error:
                    raise AmbiguousProviderSubmitError(
                        "Qwen Image 提交网络异常，远端可能已创建任务；请勿自动重提，避免重复计费"
                    ) from error
                if not response.is_success:
                    if on_submit_rejected is not None and response.status_code < 500:
                        await on_submit_rejected()
                    if response.status_code in {401, 403}:
                        raise ValueError("Qwen Image 认证失败，请检查图像 API Key")
                    if response.status_code == 429:
                        raise RecoverableProviderError(
                            f"Qwen Image 提交限流（HTTP {response.status_code}）"
                        )
                    if response.status_code >= 500:
                        raise AmbiguousProviderSubmitError(
                            f"Qwen Image 提交结果不确定（HTTP {response.status_code}）；"
                            "远端可能已创建任务，请人工确认后处理，避免重复计费"
                        )
                    raise ValueError(f"Qwen Image 提交失败（HTTP {response.status_code}）")
                try:
                    task_id = response.json().get("output", {}).get("task_id")
                except (ValueError, AttributeError) as error:
                    raise AmbiguousProviderSubmitError(
                        "Qwen Image 已响应成功，但任务编号无法解析；请勿自动重提，避免重复计费"
                    ) from error
                if not task_id:
                    raise AmbiguousProviderSubmitError(
                        "Qwen Image 提交成功但未返回任务编号；请勿自动重提，避免重复计费"
                    )
                if on_submitted is not None:
                    try:
                        await on_submitted(str(task_id))
                    except (AmbiguousProviderSubmitError, ProviderCheckpointError):
                        raise
                    except Exception as error:
                        raise AmbiguousProviderSubmitError(
                            "供应商已受理图像任务，但任务编号未能保存；请勿自动重提，避免重复计费",
                            remote_task_id=str(task_id),
                        ) from error

            image_url = ""
            settings = get_settings()
            for _ in range(settings.image_task_poll_max_attempts):
                await asyncio.sleep(settings.image_task_poll_interval_seconds)
                try:
                    task_response = await client.get(
                        f"{api_root}/tasks/{task_id}",
                        headers=auth_headers,
                    )
                except httpx.RequestError as error:
                    raise RecoverableProviderError(
                        "查询 Qwen Image 任务时网络暂时不可用"
                    ) from error
                if not task_response.is_success:
                    _raise_query_failure(task_response.status_code)
                try:
                    output = task_response.json().get("output", {})
                except (ValueError, AttributeError) as error:
                    raise RecoverableProviderError("Qwen Image 任务状态响应暂时无法读取") from error
                status = output.get("task_status")
                if status == "SUCCEEDED":
                    choices = output.get("choices") or []
                    content = choices[0].get("message", {}).get("content", []) if choices else []
                    image_item = next((item for item in content if item.get("image")), None)
                    if image_item:
                        image_url = str(image_item["image"])
                    break
                if status in _TERMINAL_REMOTE:
                    raise ValueError("Qwen Image 生成失败，请检查提示词和账户额度后重试")
            if not image_url:
                # Remote job may still be running; keep checkpoint and resume later.
                raise RecoverableProviderError("Qwen Image 任务超时或未返回图像")

            await validate_public_https_url(image_url)
            try:
                download = await client.get(image_url)
            except httpx.RequestError as error:
                raise RecoverableProviderError("下载 Qwen Image 结果时网络暂时不可用") from error
            if not download.is_success:
                if download.status_code == 429 or download.status_code >= 500:
                    raise RecoverableProviderError("下载 Qwen Image 结果失败")
                raise ValueError("下载 Qwen Image 结果失败")
            content_type = download.headers.get("content-type", "").split(";", 1)[0].lower()
            extensions = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
            extension = extensions.get(content_type)
            if not extension or len(download.content) > 20 * 1024 * 1024:
                raise ValueError("Qwen Image 返回了不支持的图片格式或过大的文件")

        try:
            return await self._store.put_bytes(f"{asset_id}{extension}", download.content)
        except Exception as error:
            raise RecoverableProviderError("保存 Qwen Image 结果时存储暂时不可用") from error


default_image_provider = QwenImageProvider()


async def generate_image(
    *,
    api_key: str,
    model: str,
    prompt: str,
    asset_id: UUID,
    base_url: str | None = None,
    resume_task_id: str | None = None,
    prompt_extend: bool = True,
    on_submit_started: Callable[[], Awaitable[None]] | None = None,
    on_submit_rejected: Callable[[], Awaitable[None]] | None = None,
    on_submitted: OnSubmitted | None = None,
) -> str:
    return await default_image_provider.generate(
        api_key=api_key,
        model=model,
        prompt=prompt,
        asset_id=asset_id,
        base_url=base_url,
        resume_task_id=resume_task_id,
        prompt_extend=prompt_extend,
        on_submit_started=on_submit_started,
        on_submit_rejected=on_submit_rejected,
        on_submitted=on_submitted,
    )


# Backward-compatible alias used by older imports/tests.
generate_qwen_image = generate_image
