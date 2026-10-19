from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.model_presets import (
    IMAGE_BACKEND_LABELS,
    IMAGE_BACKENDS,
    ImageBackend,
    SystemModelPreset,
    parse_system_presets,
    split_csv,
)
from app.core.models_catalog import DEFAULT_IMAGE_MODEL, DEFAULT_TEXT_MODEL


class Settings(BaseSettings):
    app_name: str = "Manxu Studio API"
    app_env: Literal["development", "production"] = "development"
    log_dir: Path = Path(".data/logs")
    database_url: str = "postgresql+asyncpg://manxu:manxu@localhost:55442/manxu_dev"
    cors_origins: str = "http://localhost:5173"
    github_client_id: str = ""
    github_client_secret: str = ""
    github_callback_url: str = "http://localhost:8000/api/v1/auth/github/callback"
    frontend_base_url: str = "http://localhost:5173"
    session_cookie_secure: bool = False
    session_cookie_name: str = "manxu_session"
    session_ttl_days: int = 30
    model_encryption_key: str = ""
    image_storage_dir: str = "./var/images"
    object_store_backend: Literal["local", "s3"] = "local"
    s3_endpoint: str = ""
    s3_region: str = "ap-guangzhou"
    s3_bucket: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_addressing_style: Literal["virtual", "path"] = "virtual"
    qwen_image_base_url: str = "https://dashscope.aliyuncs.com/api/v1"
    # Legacy single-preset fields kept as fallback when MODEL_SYSTEM_PRESETS is empty.
    model_preset_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model_preset_text_model: str = DEFAULT_TEXT_MODEL
    model_preset_image_model: str = DEFAULT_IMAGE_MODEL
    # JSON array of SystemModelPreset; empty uses built-in Qwen + Agnes defaults.
    model_system_presets: str = ""
    image_model_concurrency: int = 2
    image_model_negative_prompt: str = "text, watermark, signature, extra fingers, deformed hands"
    image_model_allowlist: str = (
        "qwen-image-3.0,qwen-image-3.0-pro,qwen-image-2.1-pro,qwen-image-2.1-turbo"
    )
    openai_image_model_allowlist: str = (
        "agnes-image-2.5-flash,agnes-image-2.1-flash,agnes-image-2.0-flash"
    )
    # ARQ job wall clock; must exceed provider poll budget + margin.
    generation_job_timeout_seconds: int = Field(default=960, ge=120, le=3600)
    # Reclaim running tasks with no heartbeat after this many seconds.
    generation_stale_running_seconds: int = Field(default=900, ge=60, le=3600)
    image_task_poll_interval_seconds: int = Field(default=5, ge=1, le=60)
    image_task_poll_max_attempts: int = Field(default=120, ge=1, le=1000)
    redis_url: str = "redis://localhost:56379/0"
    email_code_pepper: str = ""
    email_code_ttl_seconds: int = 600
    email_code_resend_seconds: int = 60
    email_code_max_attempts: int = 5
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_starttls: bool = True
    rate_limit_per_minute: int = 30
    read_rate_limit_per_minute: int = 120
    # Playground/Compose only: allow http://fake-llm and other private base URLs.
    allow_private_model_base_urls: bool = False

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    @model_validator(mode="after")
    def validate_generation_sla(self) -> Self:
        if self.generation_stale_running_seconds >= self.generation_job_timeout_seconds:
            raise ValueError(
                "generation_stale_running_seconds must be less than generation_job_timeout_seconds"
            )
        poll_budget = self.image_task_poll_interval_seconds * self.image_task_poll_max_attempts
        max_poll_budget = self.generation_job_timeout_seconds - 60
        if poll_budget > max_poll_budget:
            raise ValueError(
                "image_task_poll_interval_seconds * image_task_poll_max_attempts "
                "must be <= generation_job_timeout_seconds - 60"
            )
        if self.object_store_backend == "s3":
            missing = [
                name
                for name, value in (
                    ("S3_ENDPOINT", self.s3_endpoint),
                    ("S3_BUCKET", self.s3_bucket),
                    ("S3_ACCESS_KEY_ID", self.s3_access_key_id),
                    ("S3_SECRET_ACCESS_KEY", self.s3_secret_access_key),
                )
                if not value.strip()
            ]
            if missing:
                raise ValueError("object_store_backend=s3 requires " + ", ".join(missing))
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def image_model_allowlist_values(self) -> list[str]:
        """Qwen async allowlist (backward-compatible name)."""
        return split_csv(self.image_model_allowlist)

    @property
    def openai_image_model_allowlist_values(self) -> list[str]:
        return split_csv(self.openai_image_model_allowlist)

    def image_models_for_backend(self, backend: ImageBackend) -> list[str]:
        if backend == "qwen_async":
            return self.image_model_allowlist_values
        return self.openai_image_model_allowlist_values

    def image_backend_options(self) -> list[dict[str, object]]:
        return [
            {
                "id": backend,
                "label": IMAGE_BACKEND_LABELS[backend],
                "models": self.image_models_for_backend(backend),
            }
            for backend in IMAGE_BACKENDS
            if self.image_models_for_backend(backend)
        ]

    def system_model_presets(self) -> list[SystemModelPreset]:
        return parse_system_presets(self.model_system_presets)

    @property
    def default_image_model(self) -> str:
        if self.model_preset_image_model:
            return self.model_preset_image_model
        allowlist = self.image_model_allowlist_values
        return allowlist[0] if allowlist else DEFAULT_IMAGE_MODEL


@lru_cache
def get_settings() -> Settings:
    return Settings()
