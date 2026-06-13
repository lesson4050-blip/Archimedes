"""Application configuration loaded from environment variables.

All settings are read from a ``.env`` file via *pydantic-settings*.
No values are hardcoded — every parameter has a sensible default that
can be overridden through environment variables.
"""

from __future__ import annotations

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

    # ── Security ────────────────────────────────────────────
    allowed_origins: str = "http://localhost:3000,http://localhost:1420"

    @property
    def cors_origins(self) -> list[str]:
        """Parse comma-separated origins into a list."""
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance."""
    return Settings()
