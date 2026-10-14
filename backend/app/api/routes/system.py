import time
from importlib.metadata import version
from typing import Literal
from urllib.parse import urljoin
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    check_csrf,
    current_account,
    decrypt_secret,
    encrypt_secret,
    validate_public_https_url,
)
from app.db.models import AccountModelConfigRecord
from app.db.session import get_session

router = APIRouter(tags=["System"])


class HealthStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"]


class VersionInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str


class ModelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text_provider: str
    text_model: str
    text_base_url: str
    text_api_key_configured: bool
    text_status: Literal["not_configured", "configured", "connected", "error"]
    image_provider: str
    image_model: str
    image_base_url: str
    image_api_key_configured: bool
    image_concurrency: int
    image_negative_prompt: str
    image_status: Literal["not_configured", "configured", "connected", "error"]
    image_models: list[str]


class ModelConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text_model: str = Field(min_length=1, max_length=160)
    text_base_url: str = Field(min_length=9, max_length=2048)
    text_api_key: str | None = Field(default=None, min_length=1, max_length=4096)
    image_base_url: str | None = Field(default=None, min_length=9, max_length=2048)
    image_model: Literal[
        "qwen-image-3.0-pro", "qwen-image-3.0", "qwen-image-2.1-pro", "qwen-image-2.1-turbo"
    ]
    image_api_key: str | None = Field(default=None, min_length=1, max_length=4096)


class ModelConnectionTest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: bool
    message: str
    latency_ms: int | None = None


SessionDep = Depends(get_session)
IMAGE_MODELS = [
    "qwen-image-3.0-pro",
    "qwen-image-3.0",
    "qwen-image-2.1-pro",
    "qwen-image-2.1-turbo",
]


@router.get("/health", operation_id="getHealth", response_model=HealthStatus)
async def get_health() -> HealthStatus:
    return HealthStatus(status="ok")


@router.get("/version", operation_id="getVersion", response_model=VersionInfo)
async def get_version() -> VersionInfo:
    return VersionInfo(version=version("manxu-api"))


async def _get_config(session: AsyncSession, account_id: UUID) -> AccountModelConfigRecord:
    config = await session.get(AccountModelConfigRecord, account_id)
    if config is None:
        config = AccountModelConfigRecord(
            account_id=account_id, image_base_url=get_settings().qwen_image_base_url
        )
        session.add(config)
        await session.flush()
    return config


def _config_view(config: AccountModelConfigRecord) -> ModelConfig:
    settings = get_settings()
    return ModelConfig(
        text_provider="openai-compatible",
        text_model=config.text_model,
        text_base_url=config.text_base_url,
        text_api_key_configured=bool(config.text_api_key_encrypted),
        text_status=config.text_status,
        image_provider="qwen",
        image_model=config.image_model,
        image_base_url=config.image_base_url or settings.qwen_image_base_url,
        image_api_key_configured=bool(config.image_api_key_encrypted),
        image_concurrency=settings.image_model_concurrency,
        image_negative_prompt=settings.image_model_negative_prompt,
        image_status=config.image_status,
        image_models=IMAGE_MODELS,
    )


@router.get("/model-config", operation_id="getModelConfig", response_model=ModelConfig)
async def get_model_config(request: Request, session: AsyncSession = SessionDep) -> ModelConfig:
    account = await current_account(request, session)
    config = await _get_config(session, account.id)
    return _config_view(config)


@router.put("/model-config", operation_id="updateModelConfig", response_model=ModelConfig)
async def update_model_config(
    body: ModelConfigUpdate,
    request: Request,
    session: AsyncSession = SessionDep,
) -> ModelConfig:
    check_csrf(request)
    account = await current_account(request, session)
    await validate_public_https_url(body.text_base_url)
    if body.image_base_url is not None:
        await validate_public_https_url(body.image_base_url)
    config = await _get_config(session, account.id)
    config.text_model = body.text_model.strip()
    config.text_base_url = body.text_base_url.rstrip("/")
    if body.image_base_url is not None:
        config.image_base_url = body.image_base_url.rstrip("/")
    config.image_model = body.image_model
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
    return _config_view(config)


@router.post(
    "/model-config/test", operation_id="testTextModelConnection", response_model=ModelConnectionTest
)
async def test_text_model_connection(
    request: Request,
    session: AsyncSession = SessionDep,
) -> ModelConnectionTest:
    check_csrf(request)
    account = await current_account(request, session)
    config = await _get_config(session, account.id)
    if not config.text_model or not config.text_base_url or not config.text_api_key_encrypted:
        return ModelConnectionTest(success=False, message="请先保存完整的文本模型配置")
    await validate_public_https_url(config.text_base_url)
    started = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
            response = await client.post(
                urljoin(config.text_base_url.rstrip("/") + "/", "chat/completions"),
                headers={
                    "Authorization": f"Bearer {decrypt_secret(config.text_api_key_encrypted)}"
                },
                json={
                    "model": config.text_model,
                    "messages": [{"role": "user", "content": "Reply with OK."}],
                    "max_tokens": 8,
                },
            )
        latency = int((time.monotonic() - started) * 1000)
        if response.is_success:
            config.text_status = "connected"
            await session.commit()
            return ModelConnectionTest(success=True, message="文本模型连接成功", latency_ms=latency)
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
        config.text_status = "error"
        await session.commit()
        return ModelConnectionTest(success=False, message="连接失败，请检查地址、密钥和网络后重试")
