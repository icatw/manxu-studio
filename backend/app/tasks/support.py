from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.model_modes import (
    BillingSource,
    ModelMode,
    billing_source_for_mode,
    normalize_model_mode,
)
from app.core.security import encrypt_secret
from app.db.models import GenerationTaskRecord
from app.services import model_config as model_config_service


@dataclass(slots=True)
class ResolvedModelConfig:
    """Provider fields for workers; plaintext never leaves service via API."""

    model_mode: ModelMode
    billing_source: BillingSource
    text_model: str
    text_base_url: str
    text_api_key_encrypted: bytes
    image_model: str
    image_base_url: str
    image_backend: str
    image_api_key_encrypted: bytes | None


async def report_progress(session: AsyncSession, task: GenerationTaskRecord, progress: int) -> None:
    current = getattr(task, "progress", None) or 0
    task.progress = max(current, progress)
    task.updated_at = datetime.now(UTC)
    await session.commit()


def _platform_resolved() -> ResolvedModelConfig:
    settings = get_settings()
    if not settings.platform_available:
        raise ValueError("平台默认模型未启用，请在设置中改用自备通义或 Agnes")
    key = encrypt_secret(settings.platform_agnes_api_key.strip())
    return ResolvedModelConfig(
        model_mode="platform",
        billing_source="platform",
        text_model=settings.platform_agnes_text_model.strip(),
        text_base_url=settings.platform_agnes_text_base_url.rstrip("/"),
        text_api_key_encrypted=key,
        image_model=settings.platform_agnes_image_model.strip(),
        image_base_url=settings.platform_agnes_image_base_url.rstrip("/"),
        image_backend="openai_images",
        image_api_key_encrypted=key,
    )


async def require_text_model(session: AsyncSession, owner_id: UUID) -> ResolvedModelConfig:
    config = await model_config_service.get_or_create_config(session, owner_id)
    mode = normalize_model_mode(getattr(config, "model_mode", None))
    if mode == "platform":
        return _platform_resolved()
    if (
        not getattr(config, "text_model", None)
        or not getattr(config, "text_base_url", None)
        or not getattr(config, "text_api_key_encrypted", None)
    ):
        raise ValueError("请先在设置中保存并测试文本模型配置")
    return ResolvedModelConfig(
        model_mode=mode,
        billing_source=billing_source_for_mode(mode),
        text_model=config.text_model,
        text_base_url=config.text_base_url,
        text_api_key_encrypted=config.text_api_key_encrypted,
        image_model=getattr(config, "image_model", "") or "",
        image_base_url=getattr(config, "image_base_url", "") or "",
        image_backend=getattr(config, "image_backend", None) or "qwen_async",
        image_api_key_encrypted=getattr(config, "image_api_key_encrypted", None),
    )


async def require_image_model(session: AsyncSession, owner_id: UUID) -> ResolvedModelConfig:
    config = await model_config_service.get_or_create_config(session, owner_id)
    mode = normalize_model_mode(getattr(config, "model_mode", None))
    if mode == "platform":
        return _platform_resolved()
    if not getattr(config, "image_api_key_encrypted", None):
        raise ValueError("请先在模型设置中配置图像模型 API Key")
    text_key = getattr(config, "text_api_key_encrypted", None)
    return ResolvedModelConfig(
        model_mode=mode,
        billing_source=billing_source_for_mode(mode),
        text_model=getattr(config, "text_model", "") or "",
        text_base_url=getattr(config, "text_base_url", "") or "",
        text_api_key_encrypted=text_key if isinstance(text_key, (bytes, bytearray)) else b"",
        image_model=getattr(config, "image_model", "") or "",
        image_base_url=getattr(config, "image_base_url", "") or "",
        image_backend=getattr(config, "image_backend", None) or "qwen_async",
        image_api_key_encrypted=config.image_api_key_encrypted,
    )


async def resolve_model_config(session: AsyncSession, owner_id: UUID) -> ResolvedModelConfig:
    """Resolve credentials for connection tests (requires text path)."""
    return await require_text_model(session, owner_id)
