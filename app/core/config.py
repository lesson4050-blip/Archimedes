"""Application configuration loaded from environment variables.

All settings are read from a ``.env`` file via *pydantic-settings*.
No values are hardcoded — every parameter has a sensible default that
can be overridden through environment variables.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration store for the Archimedes backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Core ────────────────────────────────────────────────
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True
    ollama_base_url: str = "http://localhost:11434"
    local_model: str = "qwen3:14b"

    # ── Memory ──────────────────────────────────────────────
    chroma_path: str = "./data/chroma_db"

    # ── Security ────────────────────────────────────────────
    allowed_origins: str = "http://localhost:3000,http://localhost:1420"
    jwt_secret_key: str = "change-this-to-a-long-random-string-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24
    admin_api_key: str = "change-this-admin-key"

    @property
    def cors_origins(self) -> list[str]:
        """Parse comma-separated origins into a list."""
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (created once per process)."""
    return Settings()
