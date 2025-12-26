from functools import lru_cache
from typing import Iterable
import json

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://sigap:sigap@localhost:5432/sigap"
    # Keep as string so env parsing doesn't require JSON for lists.
    # Examples: "*" | "http://localhost:5173" | "http://a,http://b" | "[\"http://a\",\"http://b\"]"
    cors_origins: str = "*"
    secret_key: str = "change-this"
    access_token_expire_minutes: int = 60
    storage_dir: str = "storage"
    google_client_id: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @computed_field  # type: ignore[misc]
    @property
    def cors_origins_list(self) -> list[str]:
        """Allow comma-separated string or JSON list in env; fallback to ["*"]."""
        raw = (self.cors_origins or "").strip()
        if not raw:
            return ["*"]
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    values = [v.strip() for v in parsed if isinstance(v, str) and v.strip()]
                    return values or ["*"]
            except json.JSONDecodeError:
                return ["*"]
        if raw == "*":
            return ["*"]
        values = [v.strip() for v in raw.split(",") if v.strip()]
        return values or ["*"]


@lru_cache
def get_settings() -> "Settings":
    return Settings()


settings = get_settings()
