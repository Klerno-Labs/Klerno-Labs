"""Top-level pytest configuration.

Placing pytest_plugins here avoids the deprecation warning when other
conftest files live in subpackages (like CLEAN_APP/tests). Tests expect
the asyncio plugin; declare it once at the repository root.
"""

import pytest

pytest_plugins = ["asyncio"]


@pytest.fixture(autouse=True)
def disable_rate_limiting_for_tests(monkeypatch) -> None:
    """Disable rate limiting for all tests."""
    monkeypatch.setenv("ENABLE_RATE_LIMIT", "false")
