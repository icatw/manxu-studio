from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.api_responses import register_exception_handlers
from app.core.config import get_settings
from app.core.logging import configure_api_logging
from app.core.middleware import ApiResponseLoggingMiddleware
from app.core.redis import close_redis_client

settings = get_settings()
configure_api_logging(app_env=settings.app_env, log_dir=settings.log_dir)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await close_redis_client()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
register_exception_handlers(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(ApiResponseLoggingMiddleware)
app.include_router(api_router, prefix="/api/v1")
