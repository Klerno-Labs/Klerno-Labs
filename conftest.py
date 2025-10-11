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


@pytest.fixture(autouse=True)
def ensure_per_test_sqlite_initialized(monkeypatch, request) -> None:
    """Ensure per-test sqlite databases (pytest tmp DBs) have legacy tables.

    Some tests create temporary sqlite files under pytest's tmpdir or use
    per-test DATABASE_URLs. The session-scoped initializer covers the
    repository-level fallback DB, but it won't affect DB files created later
    during individual tests. This lightweight fixture detects sqlite-based
    DATABASE_URL values and runs the same repo initializer against that
    URL so tests see the legacy `txs` table.

    The fixture is intentionally minimal:
    - only runs when DATABASE_URL is an sqlite URL
    - calls the repository helper `scripts.init_db_if_needed.main(url)`
    - ignores errors for non-critical failures (let tests surface real
      assertions) but logs the initializer return code for debugging
    """
    import os

    url = os.getenv("DATABASE_URL")
    if not url:
        return

    # Only handle sqlite URLs here. Avoid touching Postgres or other DBs.
    if not url.startswith("sqlite:"):
        return

    try:
        from scripts import init_db_if_needed as _init

        # Run initializer for this per-test DB. Keep failures non-fatal so
        # test assertions remain the primary failure signal, but log rc.
        rc = _init.main(url)
        if rc != 0:
            print(f"[conftest.ensure_per_test_sqlite_initialized] init returned {rc} for {url}")
    except Exception as exc:  # pragma: no cover - best-effort logging
        print(f"[conftest.ensure_per_test_sqlite_initialized] exception: {exc}")
        # Do not raise here; let tests fail on their own assertions.
