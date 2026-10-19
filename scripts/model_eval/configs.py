"""Provider presets for comparative model evaluation."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProviderEndpoint:
    kind: str  # openai_text | qwen_image | agnes_image
    base_url: str
    model: str
    api_key_env: str

    def api_key(self) -> str:
        value = os.environ.get(self.api_key_env, "").strip()
        if not value:
            raise ValueError(f"缺少环境变量 {self.api_key_env}")
        return value


@dataclass(frozen=True, slots=True)
class EvalConfig:
    id: str
    label: str
    text: ProviderEndpoint
    image: ProviderEndpoint


_DEFAULT_QWEN_TEXT_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"
_DEFAULT_QWEN_IMAGE_BASE = "https://dashscope.aliyuncs.com/api/v1"
_DEFAULT_AGNES_BASE = "https://apihub.agnes-ai.com/v1"


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default).strip() or default


def build_configs() -> dict[str, EvalConfig]:
    """Resolve presets from env overrides (models/base URLs) at call time."""

    qwen_text = ProviderEndpoint(
        kind="openai_text",
        base_url=_env("QWEN_TEXT_BASE_URL", _DEFAULT_QWEN_TEXT_BASE),
        model=_env("QWEN_TEXT_MODEL", "qwen-plus"),
        api_key_env="QWEN_TEXT_API_KEY",
    )
    qwen_image = ProviderEndpoint(
        kind="qwen_image",
        base_url=_env("QWEN_IMAGE_BASE_URL", _DEFAULT_QWEN_IMAGE_BASE),
        model=_env("QWEN_IMAGE_MODEL", "qwen-image-3.0"),
        api_key_env="QWEN_IMAGE_API_KEY",
    )
    agnes_text = ProviderEndpoint(
        kind="openai_text",
        base_url=_env("AGNES_BASE_URL", _DEFAULT_AGNES_BASE),
        model=_env("AGNES_TEXT_MODEL", "agnes-3.0-flash"),
        api_key_env="AGNES_API_KEY",
    )
    agnes_image = ProviderEndpoint(
        kind="agnes_image",
        base_url=_env("AGNES_BASE_URL", _DEFAULT_AGNES_BASE),
        model=_env("AGNES_IMAGE_MODEL", "agnes-image-2.5-flash"),
        api_key_env="AGNES_API_KEY",
    )

    return {
        "baseline": EvalConfig(
            id="baseline",
            label="Qwen text + Qwen Image (production default)",
            text=qwen_text,
            image=qwen_image,
        ),
        "agnes-full": EvalConfig(
            id="agnes-full",
            label="Agnes text + Agnes Image",
            text=agnes_text,
            image=agnes_image,
        ),
        "mix-text": EvalConfig(
            id="mix-text",
            label="Agnes text + Qwen Image",
            text=agnes_text,
            image=qwen_image,
        ),
        "mix-image": EvalConfig(
            id="mix-image",
            label="Qwen text + Agnes Image",
            text=qwen_text,
            image=agnes_image,
        ),
    }
