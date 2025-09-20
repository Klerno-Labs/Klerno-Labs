"""Settings module for Klerno Labs application."""

import os
from functools import lru_cache

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


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings: Settings = get_settings()
