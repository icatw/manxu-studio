"""Account model credential modes (MODEL-04)."""

from __future__ import annotations

from typing import Literal

ModelMode = Literal["platform", "byok_qwen", "byok_agnes"]
BillingSource = Literal["platform", "byok"]

MODEL_MODES: tuple[ModelMode, ...] = ("platform", "byok_qwen", "byok_agnes")


def normalize_model_mode(raw: str | None) -> ModelMode:
    value = (raw or "").strip()
    if value == "platform":
        return "platform"
    if value == "byok_agnes":
        return "byok_agnes"
    if value == "byok_qwen":
        return "byok_qwen"
    return "byok_qwen"


def billing_source_for_mode(mode: ModelMode) -> BillingSource:
    return "platform" if mode == "platform" else "byok"


def infer_mode_from_legacy_backend(image_backend: str | None) -> ModelMode:
    if (image_backend or "").strip() == "openai_images":
        return "byok_agnes"
    return "byok_qwen"
