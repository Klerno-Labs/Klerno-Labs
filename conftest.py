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


@pytest.fixture(scope="session", autouse=True)
def ensure_db_initialized() -> None:
    """Ensure the fallback database has core tables before any tests run.

    This reuses the repository's `scripts/init_db_if_needed.py` helper so we
    don't duplicate initialization logic. It sets a default `DATABASE_URL`
    pointing at `./data/klerno.db` when one isn't provided and calls the
    script's `main()` function.
    """
    import os
    from pathlib import Path

    try:
        # Ensure ./data exists for the default sqlite file path.
        Path("./data").mkdir(exist_ok=True)

        url = os.getenv("DATABASE_URL") or "sqlite:///./data/klerno.db"
        os.environ.setdefault("DATABASE_URL", url)

        # Import and call the repository initializer helper (no duplication).
        from scripts import init_db_if_needed as _init

        # Log what we're initializing so CI output can explain failures.
        print(f"[conftest.ensure_db_initialized] DATABASE_URL={url}")

        rc = _init.main(url)
        print(f"[conftest.ensure_db_initialized] init_db_if_needed.main returned {rc}")

        # If the helper reported an error, raise so CI fails with a clear cause.
        if rc != 0:
            raise RuntimeError(f"init_db_if_needed reported non-zero exit: {rc}")
    except Exception:
        # Re-raise so CI log captures the traceback for triage.
        raise
