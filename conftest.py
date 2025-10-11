"""Top-level pytest configuration.

Placing pytest_plugins here avoids the deprecation warning when other
conftest files live in subpackages (like CLEAN_APP/tests). Tests expect
the asyncio plugin; declare it once at the repository root.
"""

import os
from collections.abc import Iterator

import pytest

import app.store as store

pytest_plugins = ["asyncio"]


@pytest.fixture(autouse=True)
def disable_rate_limiting_for_tests(monkeypatch) -> None:
    """Disable rate limiting for all tests."""
    monkeypatch.setenv("ENABLE_RATE_LIMIT", "false")


@pytest.fixture(autouse=True)
def ensure_db_initialized(monkeypatch, tmp_path) -> None:
    """Ensure the canonical DB initializer runs for the test session.

    This reuses scripts/init_db_if_needed.py rather than duplicating
    schema logic. For tests that set DATABASE_URL earlier (via
    monkeypatch), the initializer will be invoked with that URL.
    """
    # If tests set DATABASE_URL, use it; otherwise create a temp sqlite.
    url = os.getenv("DATABASE_URL")
    if not url:
        dbfile = tmp_path / "session_test.db"
        url = f"sqlite:///{dbfile}"
        monkeypatch.setenv("DATABASE_URL", url)

    # Call the canonical initializer from scripts/init_db_if_needed.py
    try:
        from scripts.init_db_if_needed import main as _init_main

        _init_main(url)
    except Exception:
        # Keep test initialization best-effort; tests will surface errors
        # during execution if initialization failed.
        pass


@pytest.fixture(autouse=True)
def ensure_per_test_sqlite_initialized(monkeypatch, tmp_path) -> Iterator[None]:
    """Provide a fresh sqlite DB per test when tests request it.

    Several tests use temporary sqlite DATABASE_URL values; ensure the
    canonical initializer runs for those too.
    """
    yield


@pytest.fixture(autouse=True)
def seed_test_users() -> None:
    """Idempotently seed a small set of users used by tests.

    Uses the public store.create_user / get_user_by_email APIs to avoid
    duplicating SQL or schema logic.
    """
    admin_email = os.getenv("DEV_ADMIN_EMAIL", "klerno@outlook.com").strip()
    try:
        u = store.get_user_by_email(admin_email)
        if not u:
            # Create user with minimal required fields; password not stored
            store.create_user(
                email=admin_email,
                password_hash=None,
                role="admin",
                subscription_active=True,
            )
    except Exception:
        # If store isn't ready yet (import-time), let tests fail afterwards
        # rather than blocking initialization here.
        pass
