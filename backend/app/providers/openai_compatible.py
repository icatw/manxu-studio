import json
import time
from dataclasses import dataclass
from typing import TypeVar
from urllib.parse import urljoin

import httpx
from pydantic import BaseModel, ValidationError

from app.services.usage import record_usage_event

T = TypeVar("T", bound=BaseModel)

PROVIDER_NAME = "openai_compatible"


@dataclass(frozen=True, slots=True)
class TextCallMetrics:
    latency_ms: int
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class StructuredTextResult[T: BaseModel]:
    value: T
    metrics: TextCallMetrics


def _int_or_none(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _usage_from_payload(payload: dict[str, object]) -> tuple[int | None, int | None, int | None]:
    raw = payload.get("usage")
    usage = raw if isinstance(raw, dict) else {}
    prompt = _int_or_none(usage.get("prompt_tokens") or usage.get("input_tokens"))
    completion = _int_or_none(usage.get("completion_tokens") or usage.get("output_tokens"))
    total = _int_or_none(usage.get("total_tokens"))
    return prompt, completion, total


class OpenAICompatibleTextProvider:
    """OpenAI-compatible chat completions with JSON object responses."""

    async def generate_structured_with_metrics[T: BaseModel](
        self,
        *,
        base_url: str,
        model: str,
        api_key: str,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> StructuredTextResult[T]:
        endpoint = urljoin(base_url.rstrip("/") + "/", "chat/completions")
        timeout = httpx.Timeout(150, connect=10)
        started = time.perf_counter()
        try:
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
                        "temperature": 0.7,
                        "max_tokens": 5000,
                    },
                )
        except httpx.TimeoutException as error:
            raise ValueError("文本模型响应超时，请稍后重试") from error
        except httpx.HTTPError as error:
            raise ValueError("无法连接文本模型，请检查配置和网络") from error

        latency_ms = int((time.perf_counter() - started) * 1000)
        if not response.is_success:
            if response.status_code in {401, 403}:
                raise ValueError("文本模型认证失败，请检查 API Key")
            if response.status_code == 404:
                raise ValueError("文本模型 ID 或兼容接口路径无效")
            raise ValueError(f"文本模型请求失败（HTTP {response.status_code}）")

        try:
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("模型未返回文本内容")
            content = payload["choices"][0]["message"]["content"]
            if isinstance(content, list):
                content = "".join(
                    str(item.get("text", "")) for item in content if isinstance(item, dict)
                )
            if not isinstance(content, str):
                raise ValueError("模型未返回文本内容")
            parsed = json.loads(content)
            value = response_model.model_validate(parsed)
            prompt_tokens, completion_tokens, total_tokens = _usage_from_payload(payload)
            return StructuredTextResult(
                value=value,
                metrics=TextCallMetrics(
                    latency_ms=latency_ms,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                ),
            )
        except (KeyError, IndexError, TypeError, json.JSONDecodeError, ValidationError) as error:
            raise ValueError("文本模型未返回符合格式的结果，请重试") from error

    async def generate_structured[T: BaseModel](
        self,
        *,
        base_url: str,
        model: str,
        api_key: str,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> T:
        result = await self.generate_structured_with_metrics(
            base_url=base_url,
            model=model,
            api_key=api_key,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=response_model,
        )
        return result.value


default_text_provider = OpenAICompatibleTextProvider()


async def generate_structured_text[T: BaseModel](
    *,
    base_url: str,
    model: str,
    api_key: str,
    system_prompt: str,
    user_prompt: str,
    response_model: type[T],
) -> T:
    started = time.perf_counter()
    try:
        result = await default_text_provider.generate_structured_with_metrics(
            base_url=base_url,
            model=model,
            api_key=api_key,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=response_model,
        )
    except Exception as error:
        latency_ms = int((time.perf_counter() - started) * 1000)
        await record_usage_event(
            call_kind="text",
            provider=PROVIDER_NAME,
            model=model,
            outcome="failed",
            latency_ms=latency_ms,
            error_code=type(error).__name__,
        )
        raise
    await record_usage_event(
        call_kind="text",
        provider=PROVIDER_NAME,
        model=model,
        outcome="success",
        prompt_tokens=result.metrics.prompt_tokens,
        completion_tokens=result.metrics.completion_tokens,
        total_tokens=result.metrics.total_tokens,
        latency_ms=result.metrics.latency_ms,
    )
    return result.value
