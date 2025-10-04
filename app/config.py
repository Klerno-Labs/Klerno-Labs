"""Klerno Labs Configuration Module.
Uses pydantic - settings for secure, validated configuration.
"""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with secure defaults and environment variable loading."""

    # App configuration
    APP_ENV: str = Field(
        "dev",
        description="Application environment: 'dev', 'test', 'production', or 'development'",
    )
    DEBUG: bool = Field(False, description="Debug mode")
    SECRET_KEY: str = Field(
        ...,
        description="Secret key for session encryption and JWT",
    )

    # Web server
    # Default to 0.0.0.0 for local development and containerized environments.
    # This is an intentional default for dev/test; production should override via
    # environment variables.
    HOST: str = Field("0.0.0.0", description="Host to bind to")  # nosec: B104
    PORT: int = Field(8000, description="Port to bind to")
    WORKERS: int = Field(1, description="Number of uvicorn workers")

    # CORS
    ALLOWED_ORIGINS: list[str] = Field(
        ["http://localhost:8000", "http://127.0.0.1:8000", "https://klerno.com"],
        description="CORS allowed origins",
    )
    ALLOWED_ORIGIN_REGEX: str | None = Field(
        r"https://(.*\.)?onrender\.com",
        description="Regex for allowed origins (optional)",
    )

    # Database
    USE_SQLITE: bool = Field(True, description="Use SQLite instead of Postgres")
    DATABASE_URL: str | None = Field(
        None,
        description="Database connection string (can be SQLite or PostgreSQL)",
    )
    SQLITE_PATH: str = Field(
        "./data/klerno.db",
        description="Path to SQLite database (used when USE_SQLITE=true)",
    )

    # XRPL Settings
    XRPL_NET: str = Field(
        "testnet",
        description="XRPL network to use: 'mainnet', 'testnet', or 'devnet'",
    )
    DESTINATION_WALLET: str = Field(
        "rPT1Sjq2YGrBMTttX4GZHjKu9dyfzbpAYe",
        description="XRPL wallet address to receive payments",
    )
    SUB_PRICE_XRP: float = Field(10.0, description="Price in XRP for a subscription")
    SUB_DURATION_DAYS: int = Field(
        30,
        description="Duration in days for a subscription",
    )

    # Email (SendGrid)
    SENDGRID_API_KEY: str | None = Field(None, description="SendGrid API key")
    ALERT_EMAIL_FROM: str | None = Field(None, description="Email to send alerts from")
    ALERT_EMAIL_TO: str | None = Field(None, description="Email to send alerts to")

    # Security
    COOKIE_SECURE: str = Field(
        "auto",
        description="Cookie secure flag: 'auto', 'true', or 'false'",
    )
    COOKIE_SAMESITE: str = Field(
        "lax",
        description="Cookie samesite flag: 'lax', 'strict', or 'none'",
    )
    ENABLE_HSTS: bool = Field(True, description="Enable HTTP Strict Transport Security")

    # Risk threshold for alerts
    RISK_THRESHOLD: float = Field(
        0.75,
        description="Risk threshold for alerts (0.0 - 1.0)",
        ge=0.0,
        le=1.0,
    )

    # Admin email
    ADMIN_EMAIL: str | None = Field(
        None,
        description="Admin email address (gets admin role on signup)",
    )

    # Model configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    @field_validator("APP_ENV")
    def validate_app_env(cls, v: str) -> str:
        """Validate application environment."""
        if v.lower() not in {"dev", "test", "production", "development", "local"}:
            raise ValueError(
                "APP_ENV must be 'dev', 'test', 'production', 'development', or 'local'",
            )
        return v.lower()

    @field_validator("XRPL_NET")
    def validate_xrpl_net(cls, v: str) -> str:
        """Validate XRPL network."""
        if v.lower() not in {"mainnet", "testnet", "devnet"}:
            raise ValueError("XRPL_NET must be 'mainnet', 'testnet', or 'devnet'")
        return v.lower()

    @field_validator("COOKIE_SECURE")
    def validate_cookie_secure(cls, v: str) -> str:
        """Validate cookie secure setting."""
        if v.lower() not in {"auto", "true", "false"}:
            raise ValueError("COOKIE_SECURE must be 'auto', 'true', or 'false'")
        return v.lower()

    @field_validator("COOKIE_SAMESITE")
    def validate_cookie_samesite(cls, v: str) -> str:
        """Validate cookie samesite setting."""
        if v.lower() not in {"lax", "strict", "none"}:
            raise ValueError("COOKIE_SAMESITE must be 'lax', 'strict', or 'none'")
        return v.lower()

    @property
    def is_production(self) -> bool:
        """Check if the app is running in production mode."""
        return self.APP_ENV == "production"

    @property
    def use_postgres(self) -> bool:
        """Check if the app should use Postgres."""
        return not self.USE_SQLITE and self.DATABASE_URL is not None


# Create a global settings instance
# Constructing Settings() may perform validation and read env vars. This is
# expected at import-time for this application. Keep the global instance for
# backward compatibility and tests.
settings: Settings = Settings.model_construct()
