"""Test support helpers used only by tests to construct common test fixtures.

This module provides a conservative factory for Settings so tests can reliably
instantiate settings without depending on developer env vars. It's imported by
unit tests in the test-suite and is intentionally small and safe.
"""

from __future__ import annotations

from typing import Any

from .settings import Settings


def make_test_settings(**overrides: Any) -> Settings:
    """Return a Settings instance suitable for tests. Any provided overrides
    will be forwarded to the Settings constructor.
    """
    # Ensure deterministic minimal environment used by tests; do not read env
    # values from the developer machine. Pass only explicit overrides to avoid
    # surprising test behaviour.
    explicit = {
        "database_url": "sqlite:///./data/test_klerno.db",
        "redis_url": "redis://localhost:6379",
        "jwt_secret": "dev-test-secret-please-change",
        "environment": "test",
        "app_env": "test",
        "port": 8000,
        **overrides,
    }
    return Settings(**explicit)
