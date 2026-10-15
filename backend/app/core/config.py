from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


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
    qwen_image_base_url: str = "https://dashscope.aliyuncs.com/api/v1"
    model_preset_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model_preset_text_model: str = "qwen-plus"
    model_preset_image_model: str = "qwen-image-3.0-pro"
    text_model_provider: str = "demo"
    text_model_id: str = "demo-template"
    text_model_base_url: str = ""
    text_model_api_key: str = ""
    image_model_provider: str = "qwen"
    image_model_id: str = "qwen-image-3.0-pro"
    image_model_base_url: str = ""
    image_model_api_key: str = ""
    image_model_concurrency: int = 2
    image_model_negative_prompt: str = "text, watermark, signature, extra fingers, deformed hands"
    image_model_allowlist: str = (
        "qwen-image-3.0-pro,qwen-image-3.0,qwen-image-2.1-pro,qwen-image-2.1-turbo"
    )
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

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def image_model_allowlist_values(self) -> list[str]:
        return [item.strip() for item in self.image_model_allowlist.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
