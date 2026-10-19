"""OpenAI-compatible /images/generations (Agnes Image and similar gateways)."""

from __future__ import annotations

import base64
from collections.abc import Awaitable, Callable
from urllib.parse import urljoin
from uuid import UUID

import httpx

from app.core.config import get_settings
from app.core.security import validate_public_https_url
from app.providers.errors import AmbiguousProviderSubmitError, RecoverableProviderError
from app.providers.object_store import get_object_store
from app.providers.protocols import ObjectStore

OnSubmitted = Callable[[str], Awaitable[None]]


class OpenAIImagesProvider:
    """Synchronous OpenAI-style image generation with durable object storage."""

    def __init__(self, store: ObjectStore | None = None) -> None:
        self._store = store or get_object_store()

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
        del prompt_extend  # not supported by OpenAI-style images API
        settings = get_settings()
        configured = (base_url or settings.qwen_image_base_url).rstrip("/")
        await validate_public_https_url(configured)

        if resume_task_id and resume_task_id.startswith("openai-images:"):
            if self._store.find_asset_key(str(asset_id)) is not None:
                return f"/api/v1/assets/{asset_id}"

        endpoint = urljoin(configured.rstrip("/") + "/", "images/generations")
        body: dict[str, object] = {
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024",
            "response_format": "b64_json",
        }
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        timeout = httpx.Timeout(360, connect=15)

        if on_submit_started is not None:
            await on_submit_started()

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            try:
                response = await client.post(endpoint, headers=headers, json=body)
            except httpx.TimeoutException as error:
                raise AmbiguousProviderSubmitError(
                    "图像提交超时，远端可能已完成计费；请勿自动重提"
                ) from error
            except httpx.RequestError as error:
                raise AmbiguousProviderSubmitError(
                    "图像提交网络异常，远端可能已完成计费；请勿自动重提"
                ) from error

            if not response.is_success:
                if on_submit_rejected is not None and response.status_code < 500:
                    await on_submit_rejected()
                if response.status_code in {401, 403}:
                    raise ValueError("图像模型认证失败，请检查 API Key")
                if response.status_code == 429:
                    raise RecoverableProviderError(
                        f"图像模型限流（HTTP {response.status_code}）"
                    )
                if response.status_code >= 500:
                    raise AmbiguousProviderSubmitError(
                        f"图像提交结果不确定（HTTP {response.status_code}）"
                    )
                # Retry without response_format for gateways that reject it.
                if response.status_code == 400 and "response_format" in response.text:
                    body.pop("response_format", None)
                    try:
                        response = await client.post(endpoint, headers=headers, json=body)
                    except httpx.RequestError as error:
                        raise AmbiguousProviderSubmitError(
                            "图像提交网络异常，远端可能已完成计费；请勿自动重提"
                        ) from error
                if not response.is_success:
                    if on_submit_rejected is not None and response.status_code < 500:
                        await on_submit_rejected()
                    raise ValueError(f"图像生成失败（HTTP {response.status_code}）")

            remote_id = f"openai-images:{asset_id}"
            if on_submitted is not None:
                await on_submitted(remote_id)

            try:
                payload = response.json()
            except ValueError as error:
                raise RecoverableProviderError("图像响应无法解析") from error
            items = payload.get("data") or []
            if not items:
                raise ValueError("图像服务未返回结果")
            item = items[0]
            data: bytes
            content_type = "image/png"
            b64 = item.get("b64_json")
            if b64:
                data = base64.b64decode(b64)
            else:
                url = item.get("url")
                if not url:
                    raise ValueError("图像服务未返回 url 或 b64_json")
                await validate_public_https_url(str(url))
                try:
                    download = await client.get(str(url))
                except httpx.RequestError as error:
                    raise RecoverableProviderError("下载生成图像时网络暂时不可用") from error
                if not download.is_success:
                    if download.status_code == 429 or download.status_code >= 500:
                        raise RecoverableProviderError("下载生成图像失败")
                    raise ValueError("下载生成图像失败")
                data = download.content
                content_type = download.headers.get("content-type", "").split(";", 1)[0].lower()

            if len(data) > 20 * 1024 * 1024:
                raise ValueError("图像文件过大")
            extension = _extension_for(content_type)
            try:
                return await self._store.put_bytes(f"{asset_id}{extension}", data)
            except Exception as error:
                raise RecoverableProviderError("保存图像结果时存储暂时不可用") from error


def _extension_for(content_type: str) -> str:
    mapping = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
    return mapping.get(content_type, ".png")


default_openai_images_provider = OpenAIImagesProvider()
