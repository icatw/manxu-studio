"""HTTP clients for text (OpenAI-compatible) and image (Qwen async / Agnes sync)."""

from __future__ import annotations

import asyncio
import base64
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


@dataclass(slots=True)
class CallMetrics:
    latency_ms: int
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    http_status: int | None = None


@dataclass(slots=True)
class TextResult[T: BaseModel]:
    value: T
    metrics: CallMetrics
    raw_content: str


@dataclass(slots=True)
class ImageResult:
    path: Path
    metrics: CallMetrics
    provider_kind: str
    bytes_len: int


def normalize_dashscope_api_base(configured_base_url: str) -> str:
    configured = urlsplit(configured_base_url)
    path = configured.path.rstrip("/")
    if path.endswith("/compatible-mode/v1"):
        path = path[: -len("/compatible-mode/v1")]
    if not path.endswith("/api/v1"):
        path = f"{path}/api/v1" if path else "/api/v1"
    return urlunsplit((configured.scheme, configured.netloc, path, "", "")).rstrip("/")


async def generate_structured_text[T: BaseModel](
    *,
    base_url: str,
    model: str,
    api_key: str,
    system_prompt: str,
    user_prompt: str,
    response_model: type[T],
    temperature: float = 0.7,
    max_tokens: int = 5000,
) -> TextResult[T]:
    endpoint = urljoin(base_url.rstrip("/") + "/", "chat/completions")
    started = time.perf_counter()
    timeout = httpx.Timeout(180, connect=15)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        response = await client.post(
            endpoint,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "response_format": {"type": "json_object"},
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
    latency_ms = int((time.perf_counter() - started) * 1000)
    if not response.is_success:
        raise ValueError(f"文本请求失败 HTTP {response.status_code}: {response.text[:400]}")
    payload = response.json()
    content = payload["choices"][0]["message"]["content"]
    if isinstance(content, list):
        content = "".join(
            str(item.get("text", "")) for item in content if isinstance(item, dict)
        )
    if not isinstance(content, str):
        raise ValueError("文本模型未返回字符串 content")
    usage = payload.get("usage") or {}
    metrics = CallMetrics(
        latency_ms=latency_ms,
        prompt_tokens=_int_or_none(usage.get("prompt_tokens") or usage.get("input_tokens")),
        completion_tokens=_int_or_none(
            usage.get("completion_tokens") or usage.get("output_tokens")
        ),
        total_tokens=_int_or_none(usage.get("total_tokens")),
        http_status=response.status_code,
    )
    try:
        parsed = response_model.model_validate(json.loads(content))
    except (json.JSONDecodeError, ValidationError) as error:
        raise ValueError(f"文本 JSON 校验失败: {error}") from error
    return TextResult(value=parsed, metrics=metrics, raw_content=content)


async def generate_qwen_image(
    *,
    base_url: str,
    model: str,
    api_key: str,
    prompt: str,
    dest: Path,
    prompt_extend: bool = False,
    poll_interval_s: float = 2.0,
    max_polls: int = 90,
) -> ImageResult:
    api_root = normalize_dashscope_api_base(base_url)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }
    started = time.perf_counter()
    timeout = httpx.Timeout(60, connect=15)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        submit = await client.post(
            f"{api_root}/services/aigc/image-generation/generation",
            headers=headers,
            json={
                "model": model,
                "input": {"messages": [{"role": "user", "content": [{"text": prompt}]}]},
                "parameters": {"size": "1024*1024", "prompt_extend": prompt_extend},
            },
        )
        if not submit.is_success:
            raise ValueError(f"Qwen Image 提交失败 HTTP {submit.status_code}: {submit.text[:400]}")
        task_id = submit.json().get("output", {}).get("task_id")
        if not task_id:
            raise ValueError("Qwen Image 未返回 task_id")
        image_url = ""
        for _ in range(max_polls):
            await asyncio.sleep(poll_interval_s)
            probe = await client.get(f"{api_root}/tasks/{task_id}", headers=headers)
            if not probe.is_success:
                raise ValueError(f"Qwen Image 查询失败 HTTP {probe.status_code}")
            output = probe.json().get("output", {})
            status = output.get("task_status")
            if status == "SUCCEEDED":
                choices = output.get("choices") or []
                content = choices[0].get("message", {}).get("content", []) if choices else []
                image_item = next((item for item in content if item.get("image")), None)
                if image_item:
                    image_url = str(image_item["image"])
                break
            if status in {"FAILED", "CANCELED", "UNKNOWN"}:
                raise ValueError(f"Qwen Image 任务失败: {status}")
        if not image_url:
            raise ValueError("Qwen Image 轮询超时")
        download = await client.get(image_url)
        if not download.is_success:
            raise ValueError(f"下载 Qwen 图失败 HTTP {download.status_code}")
        data = download.content
        content_type = download.headers.get("content-type", "").split(";", 1)[0].lower()
        by_type = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
        suffix = by_type.get(content_type, ".png")
        dest = dest.with_suffix(suffix)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    return ImageResult(
        path=dest,
        metrics=CallMetrics(latency_ms=int((time.perf_counter() - started) * 1000)),
        provider_kind="qwen_image",
        bytes_len=len(data),
    )


async def generate_openai_compatible_image(
    *,
    base_url: str,
    model: str,
    api_key: str,
    prompt: str,
    dest: Path,
    size: str = "1024x1024",
) -> ImageResult:
    """OpenAI-style /images/generations (Aliyun MaaS compatible-mode, etc.)."""
    endpoint = urljoin(base_url.rstrip("/") + "/", "images/generations")
    started = time.perf_counter()
    timeout = httpx.Timeout(360, connect=15)
    body: dict[str, object] = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "size": size,
        "response_format": "b64_json",
    }
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        response = await client.post(
            endpoint,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=body,
        )
        if not response.is_success:
            # Some gateways reject response_format; retry with url.
            if response.status_code == 400 and "response_format" in response.text:
                body.pop("response_format", None)
                response = await client.post(
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=body,
                )
        if not response.is_success:
            raise ValueError(
                f"兼容模式出图失败 HTTP {response.status_code}: {response.text[:500]}"
            )
        payload = response.json()
        items = payload.get("data") or []
        if not items:
            raise ValueError("兼容模式出图未返回 data")
        item = items[0]
        b64 = item.get("b64_json")
        if b64:
            data = base64.b64decode(b64)
            dest = dest.with_suffix(".png")
        else:
            url = item.get("url")
            if not url:
                raise ValueError("兼容模式出图无 b64_json 也无 url")
            download = await client.get(url)
            if not download.is_success:
                raise ValueError(f"下载兼容模式图像失败 HTTP {download.status_code}")
            data = download.content
            dest = dest.with_suffix(".png")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return ImageResult(
        path=dest,
        metrics=CallMetrics(
            latency_ms=int((time.perf_counter() - started) * 1000),
            http_status=response.status_code,
        ),
        provider_kind="openai_image",
        bytes_len=len(data),
    )


def size_for_ratio(ratio: str) -> str:
    mapping = {
        "1:1": "1024x1024",
        "3:4": "768x1024",
        "4:3": "1024x768",
        "9:16": "720x1280",
        "16:9": "1280x720",
    }
    return mapping.get(ratio, "1024x1024")


async def generate_agnes_image(
    *,
    base_url: str,
    model: str,
    api_key: str,
    prompt: str,
    dest: Path,
    size: str = "1K",
    ratio: str = "1:1",
    reference_paths: list[Path] | None = None,
) -> ImageResult:
    endpoint = urljoin(base_url.rstrip("/") + "/", "images/generations")
    body: dict[str, object] = {
        "model": model,
        "prompt": prompt,
        "size": size,
        "ratio": ratio,
        "extra_body": {"response_format": "b64_json"},
    }
    if reference_paths:
        images: list[str] = []
        for path in reference_paths:
            raw = path.read_bytes()
            mime = "image/png"
            if path.suffix.lower() in {".jpg", ".jpeg"}:
                mime = "image/jpeg"
            elif path.suffix.lower() == ".webp":
                mime = "image/webp"
            encoded = base64.b64encode(raw).decode("ascii")
            images.append(f"data:{mime};base64,{encoded}")
        extra = dict(body["extra_body"])  # type: ignore[arg-type]
        extra["image"] = images
        body["extra_body"] = extra

    started = time.perf_counter()
    timeout = httpx.Timeout(360, connect=15)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        response = await client.post(
            endpoint,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=body,
        )
    latency_ms = int((time.perf_counter() - started) * 1000)
    if not response.is_success:
        raise ValueError(f"Agnes Image 失败 HTTP {response.status_code}: {response.text[:400]}")
    payload = response.json()
    items = payload.get("data") or []
    if not items:
        raise ValueError("Agnes Image 未返回 data")
    item = items[0]
    b64 = item.get("b64_json")
    if b64:
        data = base64.b64decode(b64)
        dest = dest.with_suffix(".png")
    else:
        url = item.get("url")
        if not url:
            raise ValueError("Agnes Image 无 b64_json 也无 url")
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            download = await client.get(url)
        if not download.is_success:
            raise ValueError(f"下载 Agnes 图失败 HTTP {download.status_code}")
        data = download.content
        dest = dest.with_suffix(".png")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return ImageResult(
        path=dest,
        metrics=CallMetrics(latency_ms=latency_ms, http_status=response.status_code),
        provider_kind="agnes_image",
        bytes_len=len(data),
    )


def _int_or_none(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None
