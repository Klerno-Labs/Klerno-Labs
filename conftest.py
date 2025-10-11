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
def ensure_per_test_sqlite_initialized(
    monkeypatch, tmp_path, request
) -> Iterator[None]:
    """Provide a fresh sqlite DB per test and initialize the schema.

    This reuses scripts/init_db_if_needed.py rather than duplicating
    schema logic. A unique sqlite file is created under `tmp_path` for
    each test to guarantee isolation and deterministic behavior.
    """
    # Build a unique sqlite path per test
    test_name = request.node.name
    # Keep names filesystem-safe by using the node id hash if necessary
    dbfile = tmp_path / f"{test_name}.db"
    url = f"sqlite:///{dbfile}"
    monkeypatch.setenv("DATABASE_URL", url)

    # Call the canonical initializer from scripts/init_db_if_needed.py
    try:
        from scripts.init_db_if_needed import main as _init_main

        _init_main(url)
    except Exception:
        # Best-effort initialization; let tests surface errors during run
        pass

    yield
    # tmp_path is automatically cleaned by pytest; no explicit teardown needed


@pytest.fixture(autouse=True)
def seed_test_users(ensure_per_test_sqlite_initialized) -> None:
    """Idempotently seed a small set of users used by tests.

    This fixture depends on `ensure_per_test_sqlite_initialized` so the
    DB schema is present before attempting to create users. It uses the
    public store.create_user / get_user_by_email APIs to avoid
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
