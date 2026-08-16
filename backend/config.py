"""Application settings.

Single source of configuration for the backend. Every secret and tunable is
read from the environment through this module -- no module anywhere else in the
codebase should read `os.environ` directly.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # NVIDIA NIM
    NVIDIA_API_KEY: str = ""
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_MODEL: str = "nvidia/nemotron-4-340b-instruct"

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # App
    APP_ENV: Literal["development", "staging", "production"] = "development"
    SECRET_KEY: str = ""

    # Observability
    SENTRY_DSN: str = ""

    # PDF parsing
    TESSERACT_CMD: str = ""

    # CORS: comma-separated origins allowed to call the API.
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def cors_origins(self) -> list[str]:
        """CORS_ORIGINS parsed into a list, empty entries dropped."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings singleton."""
    return Settings()


settings = get_settings()
