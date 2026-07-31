"""Environment-driven application settings."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables or a local .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "GeoEstate Intelligence API"
    api_version: str = "1.0.0"
    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = Field(
        default="postgresql+asyncpg://geoestate:geoestate@localhost:5432/geoestate",
        description="Async SQLAlchemy PostgreSQL connection URL.",
    )
    database_pool_size: int = Field(default=5, ge=1)
    database_max_overflow: int = Field(default=10, ge=0)
    geocoding_user_agent: str = "GeoEstate-Intelligence/0.1 (contact: configure-in-env)"
    geocoding_email: str | None = None
    geocoding_request_delay_seconds: float = Field(default=1.1, ge=1.0)
    geocoding_timeout_seconds: float = Field(default=15.0, gt=0)
    geocoding_retry_failed_cache: bool = False
    geocoding_locality_aliases: dict[str, str] = Field(
        default_factory=lambda: {
            "mirkhanpet": "Meerkhanpet",
            "aminpur": "Ameenpur",
            "bhongir": "Bhuvanagiri",
            "appa junction peerancheru": "Peerancheru",
            "yadagirigutta": "Yadadri",
            "shankarpalli": "Shankarpally",
        }
    )
    enrichment_batch_size: int = Field(default=100, ge=1, le=1_000)
    enrichment_progress_interval: int = Field(default=50, ge=1)


@lru_cache
def get_settings() -> Settings:
    """Return a cached immutable settings instance for dependency-free access."""
    return Settings()
