"""Dispatch image generation by account image_backend."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from uuid import UUID

from app.core.model_presets import ImageBackend
from app.providers.openai_images import default_openai_images_provider
from app.providers.qwen_image import default_image_provider as default_qwen_image_provider

OnSubmitted = Callable[[str], Awaitable[None]]


def _normalize_backend(value: str | ImageBackend) -> ImageBackend:
    raw = str(value or "qwen_async").strip()
    if raw == "openai_images":
        return "openai_images"
    return "qwen_async"


async def generate_image(
    *,
    api_key: str,
    model: str,
    prompt: str,
    asset_id: UUID,
    image_backend: str | ImageBackend = "qwen_async",
    base_url: str | None = None,
    resume_task_id: str | None = None,
    prompt_extend: bool = True,
    on_submit_started: Callable[[], Awaitable[None]] | None = None,
    on_submit_rejected: Callable[[], Awaitable[None]] | None = None,
    on_submitted: OnSubmitted | None = None,
) -> str:
    backend = _normalize_backend(image_backend)
    if backend == "openai_images":
        return await default_openai_images_provider.generate(
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
    return await default_qwen_image_provider.generate(
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
