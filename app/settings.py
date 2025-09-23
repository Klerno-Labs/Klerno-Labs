"""Settings module for Klerno Labs application."""

import os
import sys
from functools import lru_cache
from typing import Any, Dict, cast

from pydantic import BaseModel


class Settings(BaseModel):
    """Application settings with environment variable support."""

    # Database settings
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/klerno.db")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # Security settings
    jwt_secret: str = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # API settings
    api_key: str = os.getenv("API_KEY", "dev-api-key")
    risk_threshold: float = float(os.getenv("RISK_THRESHOLD", "0.75"))

    # XRPL settings
    xrpl_rpc_url: str = os.getenv("XRPL_RPC_URL", "https://s2.ripple.com:51234")
    # XRP wallet address used for demo payments and tests
    XRP_WALLET_ADDRESS: str | None = os.getenv("XRP_WALLET_ADDRESS", None)

    # Email settings
    sendgrid_api_key: str = os.getenv("SENDGRID_API_KEY", "")
    alert_email_from: str = os.getenv("ALERT_EMAIL_FROM", "alerts@example.com")
    alert_email_to: str = os.getenv("ALERT_EMAIL_TO", "you@example.com")

    # Subscription settings
    SUB_PRICE_USD: float = 29.99
    SUB_PRICE_XRP: float = 50.0

    # Environment
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"

    # Network / HTTP settings expected by some tests
    # Use a stable class-level default so direct `Settings()` instantiation
    # (used in some unit tests) yields predictable values. Runtime loads
    # that respect environment variables are created via `get_settings()`.
    port: int = 8000
    cors_origins: list[str] = ["http://localhost", "http://127.0.0.1"]

    # Backwards-compatible names used in older tests and code
    # many tests expect `app_env` and `access_token_expire_minutes`
    # Default to 'test' when not provided to make test runs more robust
    app_env: str = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "test"))
    # Provide a stable default for direct construction used in tests
    access_token_expire_minutes: int = 60

    # Admin email used by bootstrap logic in auth; keep empty by default
    admin_email: str = os.getenv("ADMIN_EMAIL", "")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    # When running under pytest, force APP_ENV to 'test' so tests that rely
    # on settings.app_env == 'test' are robust to external environment vars.
    # If running under pytest, prefer 'test' app_env so test guards behave consistently.
    if "pytest" in sys.modules:
        os.environ.setdefault("APP_ENV", "test")

    # Build a current-environment-backed settings instance so changes to
    # os.environ earlier in test collection are respected (avoids class-level
    # default evaluation at import time).
    s: Dict[str, Any] = {
        "database_url": os.getenv("DATABASE_URL", "sqlite:///./data/klerno.db"),
        "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379"),
        "jwt_secret": os.getenv("JWT_SECRET", "your-secret-key-change-in-production"),
        "jwt_algorithm": "HS256",
        "jwt_expiration_hours": int(os.getenv("JWT_EXPIRATION_HOURS", "24")),
        "api_key": os.getenv("API_KEY", "dev-api-key"),
        "risk_threshold": float(os.getenv("RISK_THRESHOLD", "0.75")),
        "xrpl_rpc_url": os.getenv("XRPL_RPC_URL", "https://s2.ripple.com:51234"),
        "XRP_WALLET_ADDRESS": os.getenv("XRP_WALLET_ADDRESS", None),
        "sendgrid_api_key": os.getenv("SENDGRID_API_KEY", ""),
        "alert_email_from": os.getenv("ALERT_EMAIL_FROM", "alerts@example.com"),
        "alert_email_to": os.getenv("ALERT_EMAIL_TO", "you@example.com"),
        "SUB_PRICE_USD": float(os.getenv("SUB_PRICE_USD", "29.99")),
        "SUB_PRICE_XRP": float(os.getenv("SUB_PRICE_XRP", "50.0")),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "debug": os.getenv("DEBUG", "False").lower() == "true",
        "port": int(os.getenv("PORT", os.getenv("APP_PORT", "8000"))),
        "cors_origins": os.getenv(
            "CORS_ORIGINS", "http://localhost,http://127.0.0.1"
        ).split(","),
        "app_env": os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "test")),
        "access_token_expire_minutes": int(
            os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
        ),
        "admin_email": os.getenv("ADMIN_EMAIL", ""),
    }

    # pydantic expects correctly typed kwargs; cast for mypy compatibility
    return Settings(**cast(Dict[str, Any], s))


settings: Settings = get_settings()
