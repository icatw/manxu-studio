from importlib.metadata import version
from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import require_rate_limit
from app.core.security import check_csrf, current_account
from app.db.session import get_session
from app.services import model_config as model_config_service
from app.services.model_config import (
    ModelConfig,
    ModelConfigUpdate,
    ModelConnectionTest,
)

router = APIRouter(tags=["System"])


class HealthStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"]


class VersionInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str


SessionDep = Depends(get_session)


@router.get("/health", operation_id="getHealth", response_model=HealthStatus)
async def get_health() -> HealthStatus:
    return HealthStatus(status="ok")


@router.get("/version", operation_id="getVersion", response_model=VersionInfo)
async def get_version() -> VersionInfo:
    return VersionInfo(version=version("manxu-api"))


@router.get("/model-config", operation_id="getModelConfig", response_model=ModelConfig)
async def get_model_config(request: Request, session: AsyncSession = SessionDep) -> ModelConfig:
    account = await current_account(request, session)
    return await model_config_service.get_model_config(session, account.id)


@router.put("/model-config", operation_id="updateModelConfig", response_model=ModelConfig)
async def update_model_config(
    body: ModelConfigUpdate,
    request: Request,
    session: AsyncSession = SessionDep,
) -> ModelConfig:
    check_csrf(request)
    account = await current_account(request, session)
    return await model_config_service.update_model_config(session, account.id, body)


@router.post(
    "/model-config/test",
    operation_id="testTextModelConnection",
    response_model=ModelConnectionTest,
    dependencies=[Depends(require_rate_limit)],
)
async def test_text_model_connection(
    request: Request,
    session: AsyncSession = SessionDep,
) -> ModelConnectionTest:
    check_csrf(request)
    account = await current_account(request, session)
    return await model_config_service.test_text_connection(session, account.id)


@router.post(
    "/model-config/test-image",
    operation_id="testImageModelConnection",
    response_model=ModelConnectionTest,
    dependencies=[Depends(require_rate_limit)],
)
async def test_image_model_connection(
    request: Request,
    session: AsyncSession = SessionDep,
) -> ModelConnectionTest:
    check_csrf(request)
    account = await current_account(request, session)
    return await model_config_service.test_image_connection(session, account.id)
