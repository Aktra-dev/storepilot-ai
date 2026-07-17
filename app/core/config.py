"""
Application configuration.

Loads settings from environment variables (via .env in local development).
No business logic belongs here — this module is configuration only.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- General ---
    APP_NAME: str = "StorePilot AI"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # --- API ---
    API_V1_PREFIX: str = "/api/v1"

    # --- Database (PostgreSQL / Supabase-compatible) ---
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/storepilot"

    # --- Security ---
    SECRET_KEY: str = "change-me-in-env"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # --- AI Provider (placeholder for future implementation) ---
    AI_PROVIDER: str = "fallback"
    AI_API_KEY: str = ""
    AI_MODEL: str = "claude-sonnet-4-5-20250929"

    # --- CORS ---
    CORS_ORIGINS: str = "*"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance, so .env is parsed only once."""
    return Settings()


settings = get_settings()
