"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the NIDAN advisory API server."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "NIDAN Predictive Failure Propagation API"
    app_version: str = "0.1.0"
    app_env: Literal["development", "staging", "production", "test"] = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql://nidan:nidan_dev_password@localhost:5432/nidan"
    redis_url: str = "redis://localhost:6379/0"
    data_mode: Literal["postgres", "fixture"] = Field(
        default="postgres",
        validation_alias="NIDAN_DATA_MODE",
    )

    cors_origins_raw: str = Field(
        default="http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173",
        validation_alias="CORS_ORIGINS",
    )

    snapshot_label: str = Field(
        default="14 Jul 2026 · 00:20 IST",
        validation_alias="NIDAN_SNAPSHOT_LABEL",
    )
    policy_version: str = Field(
        default="policy-2026.07",
        validation_alias="NIDAN_POLICY_VERSION",
    )

    fixtures_snapshot_path: Path = (
        Path(__file__).resolve().parents[1] / "db" / "fixtures_snapshot.json"
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins_raw.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
