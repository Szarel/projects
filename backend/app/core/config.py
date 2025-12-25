from functools import lru_cache
from typing import Iterable
import json

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
        """Allow comma-separated string or JSON list in env; fallback to ["*"]."""
        if value is None:
            return ["*"]
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return ["*"]
            # If it looks like JSON, try to parse it
            if raw.startswith("["):
                try:
                    parsed = json.loads(raw)
                    return [v.strip() for v in parsed if isinstance(v, str) and v.strip()]
                except json.JSONDecodeError:
                    return ["*"]
            return [v.strip() for v in raw.split(",") if v.strip()]
        return [v for v in value if isinstance(v, str) and v.strip()]


@lru_cache
def get_settings() -> "Settings":
    return Settings()


settings = get_settings()
