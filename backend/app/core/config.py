from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    APP_NAME: str = "monocle"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    # Async engine URL for runtime (asyncpg).
    # Example: postgresql+asyncpg://postgres:postgres@localhost:5432/monocle
    DATABASE_URL: str

    # Used for cookie/CORS in later steps; safe defaults for local dev.
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # Placeholder for auth work in next step.
    JWT_SECRET: str = "dev-secret-change-me"

    def sync_database_url(self) -> str:
        # Alembic runs synchronously; convert async URL to sync driver.
        # async: postgresql+asyncpg://...
        # sync:  postgresql+psycopg://...
        return self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg://")


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]

