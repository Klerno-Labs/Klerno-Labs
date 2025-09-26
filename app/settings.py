"""Settings module for Klerno Labs application.

Refactored to use pydantic BaseSettings for unified validation & env parsing.
Includes strong secret enforcement outside development/test and preserves the
public API (settings.<field>) expected by existing code/tests.
"""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from typing import Any, List

from pydantic import BaseSettings, Field, validator

WEAK_SECRETS = {
    "your-secret-key-change-in-production",
    "changeme",
    "secret",
    "dev",
}


class Settings(BaseSettings):
    # Database
    database_url: str = Field("sqlite:///./data/klerno.db", env="DATABASE_URL")
    redis_url: str = Field("redis://localhost:6379", env="REDIS_URL")

    # Security / JWT
    jwt_secret: str = Field("your-secret-key-change-in-production", env="JWT_SECRET")
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(24, env="JWT_EXPIRATION_HOURS")

    # API / risk
    api_key: str = Field("dev-api-key", env="API_KEY")
    risk_threshold: float = Field(0.75, env="RISK_THRESHOLD")

    # XRPL
    xrpl_rpc_url: str = Field("https://s2.ripple.com:51234", env="XRPL_RPC_URL")
    XRP_WALLET_ADDRESS: str | None = Field(None, env="XRP_WALLET_ADDRESS")

    # Email / notifications
    sendgrid_api_key: str = Field("", env="SENDGRID_API_KEY")
    alert_email_from: str = Field("alerts@example.com", env="ALERT_EMAIL_FROM")
    alert_email_to: str = Field("you@example.com", env="ALERT_EMAIL_TO")

    # Subscription pricing
    SUB_PRICE_USD: float = Field(29.99, env="SUB_PRICE_USD")
    SUB_PRICE_XRP: float = Field(50.0, env="SUB_PRICE_XRP")

    # Environment / runtime
    environment: str = Field("development", env="ENVIRONMENT")
    debug: bool = Field(False, env="DEBUG")
    port: int = Field(8000, env="PORT")
    cors_origins: List[str] = Field(
        ["http://localhost", "http://127.0.0.1"], env="CORS_ORIGINS"
    )

    # Backwards-compatible names
    app_env: str = Field("test", env="APP_ENV")
    access_token_expire_minutes: int = Field(15, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    admin_email: str = Field("", env="ADMIN_EMAIL")

    class Config:
        env_file = ".env"
        case_sensitive = False

    @validator("cors_origins", pre=True)
    def _split_origins(cls, v: Any) -> List[str]:  # noqa: D401
        if isinstance(v, str):
            return [o for o in (item.strip() for item in v.split(",")) if o]
        return v

    @validator("app_env", always=True)
    def _derive_app_env(cls, v: str, values: dict[str, Any]) -> str:
        # Harmonize app_env & environment when not explicitly set.
        if not v or v == "test":
            # Pytest enforcement handled separately; keep v if test.
            return v or values.get("environment", "development")
        return v

    @validator("jwt_secret")
    def _enforce_strong_secret(cls, v: str, values: dict[str, Any]):  # noqa: D401
        env_eff = (values.get("environment") or values.get("app_env") or "").lower()
        # Only enforce for non-dev/test environments.
        if env_eff and env_eff not in {"dev", "development", "local", "test"}:
            if len(v) < 16 or v.lower() in WEAK_SECRETS:
                raise ValueError(
                    "Weak jwt_secret configured for non-development environment"
                )
        return v


@lru_cache
def get_settings() -> Settings:
    # Force deterministic app_env under pytest so guards relying on 'test' behave.
    if "pytest" in sys.modules:
        os.environ.setdefault("APP_ENV", "test")
    return Settings()  # type: ignore[arg-type]


settings: Settings = get_settings()
