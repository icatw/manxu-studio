"""Live playground verification for MODEL-04 / QUOTA-01."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import httpx
import pytest

from tests.playground.conftest import unwrap

pytestmark = pytest.mark.playground


@pytest.mark.asyncio
async def test_platform_mode_default_and_byok_switch(
    api_client: httpx.AsyncClient,
    login_account: Callable[[str], Awaitable[dict[str, Any]]],
    unique_email: Callable[[], str],
    fake_llm_url: str,
) -> None:
    await login_account(unique_email())

    initial = unwrap((await api_client.get("/model-config")).json())
    assert initial["platform_available"] is True
    assert initial["model_mode"] == "platform"
    assert initial["text_api_key_configured"] is True
    assert initial["image_api_key_configured"] is True
    assert initial["quota"]["applies"] is True
    assert initial["quota"]["exhausted"] is False

    # Platform mode can plan without any account BYOK keys.
    plan = await api_client.post(
        "/projects/plan",
        json={
            "premise": "雾港来信，续写一封失踪的信。",
            "genre": "悬疑",
            "art_style": "电影感写实",
            "audience": "年轻成人",
            "chapter_count": 2,
            "aspect_ratio": "portrait",
        },
    )
    assert plan.status_code == 200, plan.text
    draft = unwrap(plan.json())
    assert draft["title"]
    assert len(draft["chapters"]) == 2

    # Switch to BYOK Agnes with fake-llm credentials.
    byok = await api_client.put(
        "/model-config",
        json={
            "model_mode": "byok_agnes",
            "text_model": "fake-text",
            "text_base_url": fake_llm_url,
            "text_api_key": "playground-fake-key",
            "image_backend": "openai_images",
            "image_model": "agnes-image-2.5-flash",
            "image_base_url": fake_llm_url,
            "image_api_key": "playground-fake-image-key",
        },
    )
    assert byok.status_code == 200, byok.text
    byok_view = unwrap(byok.json())
    assert byok_view["model_mode"] == "byok_agnes"
    assert byok_view["quota"]["applies"] is False
    assert byok_view["text_api_key_configured"] is True

    # Back to platform.
    platform = await api_client.put("/model-config", json={"model_mode": "platform"})
    assert platform.status_code == 200, platform.text
    restored = unwrap(platform.json())
    assert restored["model_mode"] == "platform"
    assert restored["quota"]["applies"] is True


@pytest.mark.asyncio
async def test_byok_qwen_mode_save(
    api_client: httpx.AsyncClient,
    login_account: Callable[[str], Awaitable[dict[str, Any]]],
    unique_email: Callable[[], str],
) -> None:
    await login_account(unique_email())
    response = await api_client.put(
        "/model-config",
        json={
            "model_mode": "byok_qwen",
            "text_model": "qwen-plus",
            "text_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "text_api_key": "not-a-real-key-for-save-only",
            "image_backend": "qwen_async",
            "image_model": "qwen-image-3.0",
            "image_base_url": "https://dashscope.aliyuncs.com/api/v1",
            "image_api_key": "not-a-real-image-key",
        },
    )
    assert response.status_code == 200, response.text
    view = unwrap(response.json())
    assert view["model_mode"] == "byok_qwen"
    assert view["image_backend"] == "qwen_async"
    assert view["quota"]["applies"] is False
