"""Shared constants and utilities to avoid circular imports.
"""

import os
from typing import Any

from fastapi import Request

# Session cookie configuration
SESSION_COOKIE = os.getenv("SESSION_COOKIE_NAME", "session")


def _cookie_kwargs(request: Request) -> dict[str, Any]:
    """Get cookie configuration for session management."""
    is_https = request.url.scheme == "https"
    return {
        "httponly": True,
        "secure": is_https,  # Only use secure cookies on HTTPS
        "samesite": "lax",
        "max_age": 60 * 60 * 24 * 7,  # 7 days
        "path": "/",
    }
