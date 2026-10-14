from importlib.metadata import version
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from app.core.config import get_settings

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
    text_status: Literal["demo", "not_connected"]
    image_provider: str
    image_model: str
    image_base_url: str
    image_api_key_configured: bool
    image_concurrency: int
    image_negative_prompt: str
    image_status: Literal["demo", "not_connected"]


@router.get("/health", operation_id="getHealth", response_model=HealthStatus)
async def get_health() -> HealthStatus:
    return HealthStatus(status="ok")


@router.get("/version", operation_id="getVersion", response_model=VersionInfo)
async def get_version() -> VersionInfo:
    return VersionInfo(version=version("manxu-api"))


@router.get("/model-config", operation_id="getModelConfig", response_model=ModelConfig)
async def get_model_config() -> ModelConfig:
    settings = get_settings()
    return ModelConfig(
        text_provider=settings.text_model_provider,
        text_model=settings.text_model_id,
        text_base_url=settings.text_model_base_url,
        text_api_key_configured=bool(settings.text_model_api_key),
        text_status="demo" if settings.text_model_provider == "demo" else "not_connected",
        image_provider=settings.image_model_provider,
        image_model=settings.image_model_id,
        image_base_url=settings.image_model_base_url,
        image_api_key_configured=bool(settings.image_model_api_key),
        image_concurrency=settings.image_model_concurrency,
        image_negative_prompt=settings.image_model_negative_prompt,
        image_status="demo" if settings.image_model_provider == "demo" else "not_connected",
    )
