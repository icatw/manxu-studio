from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Manxu Studio API"
    database_url: str = "postgresql+asyncpg://manxu:manxu@localhost:55442/manxu_dev"
    cors_origins: str = "http://localhost:5173"
    text_model_provider: str = "demo"
    text_model_id: str = "demo-template"
    text_model_base_url: str = ""
    text_model_api_key: str = ""
    image_model_provider: str = "demo"
    image_model_id: str = "demo-placeholder"
    image_model_base_url: str = ""
    image_model_api_key: str = ""
    image_model_concurrency: int = 2
    image_model_negative_prompt: str = "text, watermark, signature, extra fingers, deformed hands"

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
