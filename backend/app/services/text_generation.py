import json
from typing import TypeVar
from urllib.parse import urljoin

import httpx
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


async def generate_structured_text[T: BaseModel](
    *,
    base_url: str,
    model: str,
    api_key: str,
    system_prompt: str,
    user_prompt: str,
    response_model: type[T],
) -> T:
    endpoint = urljoin(base_url.rstrip("/") + "/", "chat/completions")
    timeout = httpx.Timeout(150, connect=10)
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

    if not response.is_success:
        if response.status_code in {401, 403}:
            raise ValueError("文本模型认证失败，请检查 API Key")
        if response.status_code == 404:
            raise ValueError("文本模型 ID 或兼容接口路径无效")
        raise ValueError(f"文本模型请求失败（HTTP {response.status_code}）")

    try:
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        if isinstance(content, list):
            content = "".join(
                str(item.get("text", "")) for item in content if isinstance(item, dict)
            )
        if not isinstance(content, str):
            raise ValueError("模型未返回文本内容")
        parsed = json.loads(content)
        return response_model.model_validate(parsed)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError, ValidationError) as error:
        raise ValueError("文本模型未返回符合格式的结果，请重试") from error
