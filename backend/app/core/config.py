from functools import lru_cache
from typing import Iterable

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://sigap:sigap@localhost:5432/sigap"
    cors_origins: list[str] = ["*"]
    secret_key: str = "change-this"
    access_token_expire_minutes: int = 60
    storage_dir: str = "storage"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | Iterable[str]) -> list[str]:
        """Allow comma-separated string or JSON list in env."""
        if isinstance(value, str):
            return [v.strip() for v in value.split(",") if v.strip()]
        return list(value)


@lru_cache
def get_settings() -> "Settings":
    return Settings()


settings = get_settings()
