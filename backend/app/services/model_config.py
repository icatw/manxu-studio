"""Account model-config application service (MODEL-01…04, QUOTA-01)."""

from __future__ import annotations

import time
from typing import Literal, cast
from urllib.parse import urljoin
from uuid import UUID

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.model_modes import ModelMode, infer_mode_from_legacy_backend, normalize_model_mode
from app.core.model_presets import ImageBackend, SystemModelPreset
from app.core.security import (
    decrypt_secret,
    encrypt_secret,
    validate_public_https_url,
)
from app.db.models import AccountModelConfigRecord
from app.services.platform_quota import quota_status_for_account


class ImageBackendOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: ImageBackend
    label: str
    models: list[str]


class ModelPreset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    text_base_url: str
    image_base_url: str
    text_model: str
    image_model: str
    image_backend: ImageBackend


class ModelQuotaStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    applies: bool
    text_remaining: int | None = None
    image_remaining: int | None = None
    exhausted: bool
    message: str | None = None


class ModelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_mode: ModelMode
    platform_available: bool
    text_provider: str
    text_model: str
    text_base_url: str
    text_api_key_configured: bool
    text_status: Literal["not_configured", "configured", "connected", "error"]
    image_provider: str
    image_backend: ImageBackend
    image_model: str
    image_base_url: str
    image_api_key_configured: bool
    image_concurrency: int
    image_negative_prompt: str
    image_status: Literal["not_configured", "configured", "connected", "error"]
    image_models: list[str]
    image_backends: list[ImageBackendOption]
    system_presets: list[ModelPreset]
    quota: ModelQuotaStatus


class ModelConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_mode: ModelMode
    text_model: str | None = Field(default=None, min_length=1, max_length=160)
    text_base_url: str | None = Field(default=None, min_length=9, max_length=2048)
    text_api_key: str | None = Field(default=None, min_length=1, max_length=4096)
    image_backend: ImageBackend | None = None
    image_base_url: str | None = Field(default=None, min_length=9, max_length=2048)
    image_model: str | None = Field(default=None, min_length=1, max_length=80)
    image_api_key: str | None = Field(default=None, min_length=1, max_length=4096)


class ModelConnectionTest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: bool
    message: str
    latency_ms: int | None = None


def _normalize_backend(raw: str | None) -> ImageBackend:
    value = (raw or "qwen_async").strip()
    if value == "openai_images":
        return "openai_images"
    return "qwen_async"


def _preset_view(preset: SystemModelPreset) -> ModelPreset:
    return ModelPreset(
        id=preset.id,
        label=preset.label,
        text_base_url=preset.text_base_url,
        image_base_url=preset.image_base_url,
        text_model=preset.text_model,
        image_model=preset.image_model,
        image_backend=preset.image_backend,
    )


def _default_mode_for_new_account() -> ModelMode:
    return "platform" if get_settings().platform_available else "byok_qwen"


async def get_or_create_config(session: AsyncSession, account_id: UUID) -> AccountModelConfigRecord:
    config = await session.get(AccountModelConfigRecord, account_id)
    if config is None:
        mode = _default_mode_for_new_account()
        config = AccountModelConfigRecord(
            account_id=account_id,
            model_mode=mode,
            image_base_url=get_settings().qwen_image_base_url,
            image_backend="qwen_async" if mode != "byok_agnes" else "openai_images",
        )
        session.add(config)
        await session.flush()
    elif not getattr(config, "model_mode", None):
        backend = getattr(config, "image_backend", None)
        config.model_mode = infer_mode_from_legacy_backend(
            backend if isinstance(backend, str) else None
        )
        if isinstance(config, AccountModelConfigRecord):
            await session.flush()
    return config


def _effective_view_fields(
    config: AccountModelConfigRecord,
) -> tuple[ModelMode, str, str, ImageBackend, str, str, bool, bool, str, str]:
    settings = get_settings()
    mode = normalize_model_mode(getattr(config, "model_mode", None))
    if mode == "platform" and settings.platform_available:
        return (
            mode,
            settings.platform_agnes_text_model,
            settings.platform_agnes_text_base_url.rstrip("/"),
            "openai_images",
            settings.platform_agnes_image_model,
            settings.platform_agnes_image_base_url.rstrip("/"),
            True,
            True,
            "configured",
            "configured",
        )
    backend = _normalize_backend(getattr(config, "image_backend", None))
    text_configured = bool(config.text_api_key_encrypted)
    image_configured = bool(config.image_api_key_encrypted)
    return (
        mode,
        config.text_model,
        config.text_base_url,
        backend,
        config.image_model,
        config.image_base_url or settings.qwen_image_base_url,
        text_configured,
        image_configured,
        config.text_status or "not_configured",
        config.image_status or "not_configured",
    )


async def config_view(session: AsyncSession, config: AccountModelConfigRecord) -> ModelConfig:
    settings = get_settings()
    (
        mode,
        text_model,
        text_base_url,
        backend,
        image_model,
        image_base_url,
        text_key_ok,
        image_key_ok,
        text_status,
        image_status,
    ) = _effective_view_fields(config)
    backends = [
        ImageBackendOption.model_validate(item) for item in settings.image_backend_options()
    ]
    quota_raw = await quota_status_for_account(session, config.account_id, model_mode=mode)
    return ModelConfig(
        model_mode=mode,
        platform_available=settings.platform_available,
        text_provider="openai-compatible",
        text_model=text_model,
        text_base_url=text_base_url,
        text_api_key_configured=text_key_ok,
        text_status=cast(
            Literal["not_configured", "configured", "connected", "error"],
            text_status,
        ),
        image_provider=backend,
        image_backend=backend,
        image_model=image_model,
        image_base_url=image_base_url,
        image_api_key_configured=image_key_ok,
        image_concurrency=settings.image_model_concurrency,
        image_negative_prompt=settings.image_model_negative_prompt,
        image_status=cast(
            Literal["not_configured", "configured", "connected", "error"],
            image_status,
        ),
        image_models=settings.image_models_for_backend(backend),
        image_backends=backends,
        system_presets=[_preset_view(item) for item in settings.system_model_presets()],
        quota=ModelQuotaStatus.model_validate(quota_raw),
    )


async def get_model_config(session: AsyncSession, account_id: UUID) -> ModelConfig:
    config = await get_or_create_config(session, account_id)
    return await config_view(session, config)


def _apply_byok_preset(config: AccountModelConfigRecord, mode: ModelMode) -> None:
    settings = get_settings()
    presets = {item.id: item for item in settings.system_model_presets()}
    if mode == "byok_qwen":
        preset = presets.get("dashscope-default")
        config.image_backend = "qwen_async"
        if preset:
            config.text_model = preset.text_model
            config.text_base_url = preset.text_base_url.rstrip("/")
            config.image_model = preset.image_model
            config.image_base_url = preset.image_base_url.rstrip("/")
        else:
            config.image_base_url = settings.qwen_image_base_url
    elif mode == "byok_agnes":
        preset = presets.get("agnes-default")
        config.image_backend = "openai_images"
        if preset:
            config.text_model = preset.text_model
            config.text_base_url = preset.text_base_url.rstrip("/")
            config.image_model = preset.image_model
            config.image_base_url = preset.image_base_url.rstrip("/")


async def update_model_config(
    session: AsyncSession, account_id: UUID, body: ModelConfigUpdate
) -> ModelConfig:
    settings = get_settings()
    mode = body.model_mode
    if mode == "platform" and not settings.platform_available:
        raise HTTPException(status_code=422, detail="平台默认模型未配置，请选择自备通义或 Agnes")
    config = await get_or_create_config(session, account_id)
    config.model_mode = mode
    if mode == "platform":
        config.text_status = "configured"
        config.image_status = "configured"
        await session.commit()
        return await config_view(session, config)

    # BYOK: apply preset defaults when fields omitted, then overlay explicit body fields.
    if body.text_model is None and body.text_base_url is None and body.image_model is None:
        _apply_byok_preset(config, mode)

    if body.text_base_url is not None:
        await validate_public_https_url(body.text_base_url)
        config.text_base_url = body.text_base_url.rstrip("/")
    if body.text_model is not None:
        config.text_model = body.text_model.strip()
    if body.image_base_url is not None:
        await validate_public_https_url(body.image_base_url)
        config.image_base_url = body.image_base_url.rstrip("/")

    expected_backend: ImageBackend = "qwen_async" if mode == "byok_qwen" else "openai_images"
    backend = body.image_backend or expected_backend
    if backend != expected_backend:
        raise HTTPException(
            status_code=422,
            detail="图像后端须与所选模式一致（通义用 qwen_async，Agnes 用 openai_images）",
        )
    config.image_backend = backend
    image_model = (body.image_model or config.image_model or "").strip()
    allowed = settings.image_models_for_backend(backend)
    if image_model not in allowed:
        raise HTTPException(
            status_code=422, detail="不支持的图像模型，请从当前后端的推荐列表中选择"
        )
    config.image_model = image_model

    if not config.text_model or not config.text_base_url:
        _apply_byok_preset(config, mode)
    if not config.text_model or not config.text_base_url:
        raise HTTPException(status_code=422, detail="请填写文本模型 ID 与 Base URL")

    if "text_api_key" in body.model_fields_set:
        config.text_api_key_encrypted = (
            encrypt_secret(body.text_api_key) if body.text_api_key else None
        )
    if "image_api_key" in body.model_fields_set:
        config.image_api_key_encrypted = (
            encrypt_secret(body.image_api_key) if body.image_api_key else None
        )
    config.text_status = "configured" if config.text_api_key_encrypted else "not_configured"
    config.image_status = "configured" if config.image_api_key_encrypted else "not_configured"
    await session.commit()
    return await config_view(session, config)


async def test_text_connection(session: AsyncSession, account_id: UUID) -> ModelConnectionTest:
    from app.tasks.support import resolve_model_config

    try:
        resolved = await resolve_model_config(session, account_id)
    except ValueError as error:
        return ModelConnectionTest(success=False, message=str(error))
    await validate_public_https_url(resolved.text_base_url)
    started = time.monotonic()
    config = await get_or_create_config(session, account_id)
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
            response = await client.post(
                urljoin(resolved.text_base_url.rstrip("/") + "/", "chat/completions"),
                headers={
                    "Authorization": f"Bearer {decrypt_secret(resolved.text_api_key_encrypted)}"
                },
                json={
                    "model": resolved.text_model,
                    "messages": [{"role": "user", "content": "Reply with OK."}],
                    "max_tokens": 8,
                },
            )
        latency = int((time.monotonic() - started) * 1000)
        if response.is_success:
            if resolved.model_mode != "platform":
                config.text_status = "connected"
                await session.commit()
            return ModelConnectionTest(success=True, message="文本模型连接成功", latency_ms=latency)
        if resolved.model_mode != "platform":
            config.text_status = "error"
            await session.commit()
        if response.status_code in {401, 403}:
            message = "认证失败，请检查 API Key"
        elif response.status_code == 404:
            message = "模型或接口路径不存在，请检查模型 ID 与 Base URL"
        else:
            message = f"模型服务返回 HTTP {response.status_code}"
        return ModelConnectionTest(success=False, message=message, latency_ms=latency)
    except (httpx.HTTPError, RuntimeError, ValueError):
        if resolved.model_mode != "platform":
            config.text_status = "error"
            await session.commit()
        return ModelConnectionTest(success=False, message="连接失败，请检查地址、密钥和网络后重试")


async def test_image_connection(session: AsyncSession, account_id: UUID) -> ModelConnectionTest:
    from app.tasks.support import resolve_model_config

    try:
        resolved = await resolve_model_config(session, account_id)
    except ValueError as error:
        return ModelConnectionTest(success=False, message=str(error))
    if not resolved.image_api_key_encrypted:
        return ModelConnectionTest(success=False, message="请先保存完整的图像模型配置")
    await validate_public_https_url(resolved.image_base_url)
    backend = _normalize_backend(resolved.image_backend)
    started = time.monotonic()
    config = await get_or_create_config(session, account_id)
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
            if backend == "openai_images":
                response = await client.get(
                    urljoin(resolved.image_base_url.rstrip("/") + "/", "models"),
                    headers={
                        "Authorization": (
                            f"Bearer {decrypt_secret(resolved.image_api_key_encrypted)}"
                        )
                    },
                )
                if response.status_code == 404:
                    latency = int((time.monotonic() - started) * 1000)
                    if resolved.model_mode != "platform":
                        config.image_status = "configured"
                        await session.commit()
                    return ModelConnectionTest(
                        success=True,
                        message="图像后端已保存（网关未提供 /models，跳过探测）",
                        latency_ms=latency,
                    )
            else:
                response = await client.get(
                    urljoin(resolved.image_base_url.rstrip("/") + "/", "models"),
                    headers={
                        "Authorization": (
                            f"Bearer {decrypt_secret(resolved.image_api_key_encrypted)}"
                        )
                    },
                )
        latency = int((time.monotonic() - started) * 1000)
        if response.is_success:
            if resolved.model_mode != "platform":
                config.image_status = "connected"
                await session.commit()
            return ModelConnectionTest(success=True, message="图像模型连接成功", latency_ms=latency)
        if resolved.model_mode != "platform":
            config.image_status = "error"
            await session.commit()
        if response.status_code in {401, 403}:
            message = "认证失败，请检查图像 API Key"
        elif response.status_code == 404:
            message = "图像服务接口不存在，请检查 Base URL"
        else:
            message = f"图像服务返回 HTTP {response.status_code}"
        return ModelConnectionTest(success=False, message=message, latency_ms=latency)
    except (httpx.HTTPError, RuntimeError, ValueError):
        if resolved.model_mode != "platform":
            config.image_status = "error"
            await session.commit()
        return ModelConnectionTest(success=False, message="连接失败，请检查地址、密钥和网络后重试")
