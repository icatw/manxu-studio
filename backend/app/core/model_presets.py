"""Server-owned model presets and image-backend allowlists (env-overridable)."""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

ImageBackend = Literal["qwen_async", "openai_images"]

IMAGE_BACKENDS: tuple[ImageBackend, ...] = ("qwen_async", "openai_images")

IMAGE_BACKEND_LABELS: dict[ImageBackend, str] = {
    "qwen_async": "Qwen Image（异步）",
    "openai_images": "OpenAI 兼容出图（如 Agnes）",
}


class SystemModelPreset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=120)
    text_base_url: str = Field(min_length=9, max_length=2048)
    image_base_url: str = Field(min_length=9, max_length=2048)
    text_model: str = Field(min_length=1, max_length=160)
    image_model: str = Field(min_length=1, max_length=80)
    image_backend: ImageBackend


DEFAULT_SYSTEM_PRESETS: list[dict[str, Any]] = [
    {
        "id": "dashscope-default",
        "label": "通义百炼（Qwen）",
        "text_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "image_base_url": "https://dashscope.aliyuncs.com/api/v1",
        "text_model": "qwen-plus",
        "image_model": "qwen-image-3.0",
        "image_backend": "qwen_async",
    },
    {
        "id": "agnes-default",
        "label": "Agnes AI",
        "text_base_url": "https://apihub.agnes-ai.com/v1",
        "image_base_url": "https://apihub.agnes-ai.com/v1",
        "text_model": "agnes-3.0-flash",
        "image_model": "agnes-image-2.5-flash",
        "image_backend": "openai_images",
    },
]


def parse_system_presets(raw: str | None) -> list[SystemModelPreset]:
    """Parse MODEL_SYSTEM_PRESETS JSON; empty/invalid falls back to defaults."""
    text = (raw or "").strip()
    if not text:
        payload: Any = DEFAULT_SYSTEM_PRESETS
    else:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as error:
            raise ValueError("MODEL_SYSTEM_PRESETS must be valid JSON") from error
    if not isinstance(payload, list) or not payload:
        raise ValueError("MODEL_SYSTEM_PRESETS must be a non-empty JSON array")
    try:
        return [SystemModelPreset.model_validate(item) for item in payload]
    except ValidationError as error:
        raise ValueError(f"MODEL_SYSTEM_PRESETS invalid: {error}") from error


def split_csv(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]
