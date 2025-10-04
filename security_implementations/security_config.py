#!/usr/bin/env python3
"""Security configuration management."""

import os
from functools import lru_cache
from typing import Any


class SecurityConfig:
    """Centralized security configuration management."""

    def __init__(self):
        """Initialize security configuration."""
        self.environment = os.getenv("ENVIRONMENT", "development")

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    @property
    def debug_mode(self) -> bool:
        """Debug mode setting - should be False in production."""
        if self.is_production:
            return False
        return os.getenv("DEBUG", "False").lower() == "true"

    @property
    def secret_key(self) -> str:
        """Get secret key for JWT and other cryptographic operations."""
        secret = os.getenv("SECRET_KEY")
        if not secret:
            if self.is_production:
                raise ValueError(
                    "SECRET_KEY environment variable is required in production"
                )
            # Development fallback (never use in production)
            return "dev-secret-key-change-in-production"
        return secret

    @property
    def database_url(self) -> str:
        """Get database URL."""
        return os.getenv("DATABASE_URL", "sqlite:///./data/klerno.db")

    @property
    def allowed_origins(self) -> list:
        """Get allowed CORS origins."""
        origins = os.getenv("ALLOWED_ORIGINS", "")
        if origins:
            return [origin.strip() for origin in origins.split(",")]

        # Default origins based on environment
        if self.is_production:
            return []  # Must be explicitly configured in production
        else:
            return ["http://localhost:3000", "http://localhost:8080"]

    @property
    def rate_limit_requests(self) -> int:
        """Get rate limit for requests per minute."""
        return int(os.getenv("RATE_LIMIT_REQUESTS", "100"))

    @property
    def rate_limit_window(self) -> int:
        """Get rate limit window in seconds."""
        return int(os.getenv("RATE_LIMIT_WINDOW", "60"))

    @property
    def jwt_algorithm(self) -> str:
        """Get JWT algorithm."""
        return os.getenv("JWT_ALGORITHM", "HS256")

    @property
    def jwt_expiration_hours(self) -> int:
        """Get JWT token expiration in hours."""
        return int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

    @property
    def max_request_size(self) -> int:
        """Get maximum request size in bytes."""
        return int(os.getenv("MAX_REQUEST_SIZE", str(10 * 1024 * 1024)))  # 10MB default

    @property
    def log_level(self) -> str:
        """Get logging level."""
        if self.is_production:
            return os.getenv("LOG_LEVEL", "INFO")
        return os.getenv("LOG_LEVEL", "DEBUG")

    @property
    def security_headers(self) -> dict[str, str]:
        """Get security headers configuration."""
        base_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }

        if self.is_production:
            base_headers.update(
                {
                    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                    "Content-Security-Policy": self._get_csp_header(),
                }
            )

        return base_headers

    def _get_csp_header(self) -> str:
        """Get Content Security Policy header."""
        return (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
            "font-src 'self'; "
            "object-src 'none'; "
            "media-src 'self'; "
            "frame-src 'none';"
        )

    def validate_configuration(self) -> dict[str, Any]:
        """Validate security configuration and return status."""

        issues = []
        warnings = []

        # Check critical configuration
        if self.is_production:
            if not os.getenv("SECRET_KEY"):
                issues.append("SECRET_KEY not configured for production")

            if self.debug_mode:
                issues.append("Debug mode enabled in production")

            if not self.allowed_origins:
                warnings.append("No CORS origins configured for production")

        # Check secret key strength
        if len(self.secret_key) < 32:
            warnings.append("Secret key should be at least 32 characters long")

        return {
            "environment": self.environment,
            "is_production": self.is_production,
            "debug_mode": self.debug_mode,
            "critical_issues": issues,
            "warnings": warnings,
            "configuration_valid": len(issues) == 0,
        }


@lru_cache
def get_security_config() -> SecurityConfig:
    """Get cached security configuration instance."""
    return SecurityConfig()


# Example usage:
# from security_config import get_security_config
#
# config = get_security_config()
# if config.is_production and config.debug_mode:
#     raise ValueError("Debug mode must be disabled in production")
