"""Security package shims.

Provide a couple of tiny compatibility helpers expected by legacy
modules (tests and paywall.py import expected_api_key).
"""

from typing import Any

from . import encryption  # re-export for convenience

__all__ = ["encryption", "enforce_api_key", "expected_api_key"]


def expected_api_key() -> str | None:
    """Return an API key expected by older code paths.

    Read from environment variable PAYWALL_API_KEY if set.
    """
    import os

    return os.getenv("PAYWALL_API_KEY")


def enforce_api_key(header_value: str | None) -> bool:
    """Simple compatibility helper that verifies an API key header.

    Old tests patch this function when they want to bypass API key checks.
    """
    expected = expected_api_key()
    if expected is None:
        # No API key required in test/dev environment
        return True
    return header_value == expected


def preview_api_key() -> dict[str, Any]:
    """Return a minimal masked preview for an API key (compat shim).

    Tests and admin endpoints import preview_api_key from app.security; provide
    a lightweight implementation here that mirrors the behavior of the
    original module.
    """
    key = expected_api_key()
    if not key:
        return {"configured": False}
    preview = (key[:4] + "..." + key[-4:]) if len(key) >= 8 else "***"
    return {
        "configured": True,
        "preview": preview,
        "updated_at": None,
        "source": "env",
    }


def rotate_api_key() -> str:
    """Generate and return a new API key string (compat shim).

    This is a lightweight implementation used by admin/test code. It does not
    persist the key to disk but returns a syntactically valid key.
    """
    import secrets

    return "sk-" + secrets.token_urlsafe(32)
