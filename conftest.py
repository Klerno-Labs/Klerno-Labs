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
def mock_neon_httpx():
    """Stub out Neon Data API HTTP calls to make tests deterministic.

    This replaces httpx.AsyncClient with a thin wrapper that intercepts
    requests whose URL starts with the configured Neon base URL
    (VITE_NEON_DATA_API_URL / NEON_DATA_API_URL) and returns a small
    deterministic JSON payload. Non-Neon requests are proxied to the
    real AsyncClient.
    """
    try:
        import os

        import httpx

        RealAsyncClient = httpx.AsyncClient

        class _FakeResponse:
            def __init__(self, status_code=200, body=None):
                self.status_code = status_code
                self._body = body if body is not None else []
                # text used in some error paths
                try:
                    import json as _json

                    self.text = _json.dumps(self._body)
                except Exception:
                    self.text = str(self._body)

            def json(self):
                return self._body

        class FakeAsyncClient:
            """Minimal proxy that intercepts Neon Data API calls.

            It mirrors the subset of AsyncClient used in the app: async
            context manager + .get/.request. Other attributes are proxied
            to the real client instance.
            """

            def __init__(self, *args, **kwargs):
                # create a real client for non-intercepted requests
                self._client = RealAsyncClient(*args, **kwargs)

            async def __aenter__(self):
                await self._client.__aenter__()
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return await self._client.__aexit__(exc_type, exc, tb)

            async def request(self, method, url, *args, **kwargs):
                base = (
                    os.getenv("VITE_NEON_DATA_API_URL")
                    or os.getenv("NEON_DATA_API_URL")
                    or ""
                ).rstrip("/")
                # Normalize comparison: requests in code build full URLs
                if base and isinstance(url, str) and url.startswith(base):
                    # Extract headers for inspection
                    headers = kwargs.get("headers") or {}

                    # If the configured base points at an intentionally invalid
                    # host (tests commonly set to https://example.invalid),
                    # simulate a connection error to reproduce app error paths.
                    if "example.invalid" in base:
                        raise httpx.RequestError("Simulated Neon connection error")

                    # If the client did not send Authorization, return 401
                    # to emulate the Neon API protecting endpoints.
                    if not headers.get("Authorization"):
                        return _FakeResponse(
                            status_code=401, body={"error": "Unauthorized"}
                        )

                    # Otherwise return an empty list payload for list-style
                    # endpoints like /notes and /paragraphs.
                    return _FakeResponse(status_code=200, body=[])

                # Proxy to real client for anything else
                return await self._client.request(method, url, *args, **kwargs)

            async def get(self, url, *args, **kwargs):
                return await self.request("GET", url, *args, **kwargs)

            # Allow tests / code to access other attributes on the real client
            def __getattr__(self, name):
                return getattr(self._client, name)

        # Patch httpx.AsyncClient for the session and restore on teardown.
        Real = getattr(httpx, "AsyncClient", None)
        httpx.AsyncClient = FakeAsyncClient
        try:
            yield
        finally:
            # Restore original symbol
            if Real is not None:
                httpx.AsyncClient = Real
            else:
                with __import__("contextlib").suppress(Exception):
                    delattr(httpx, "AsyncClient")
    except Exception:
        # If anything goes wrong patching httpx, let tests proceed using the
        # real client; failures will surface in tests instead of hiding them.
        with __import__("contextlib").suppress(Exception):
            _ = None


@pytest.fixture(scope="session", autouse=True)
def seed_default_admin(ensure_db_initialized) -> None:
    """Create a deterministic admin user if one doesn't already exist.

    This helps tests that assume an admin account or seeded data. It
    depends on `ensure_db_initialized` so schema creation runs first.
    The fixture is idempotent.
    """
    try:
        from app import store

    # Common admin email used by a handful of tests; create if missing.
    # Use the project's test/admin account configured by the user.
    admin_email = "klerno@outlook.com"
        with __import__("contextlib").suppress(Exception):
            existing = store.get_user_by_email(admin_email)
            if not existing:
                # password_hash may be None for tests; role must be 'admin'
                store.create_user(
                    admin_email,
                    password_hash=None,
                    role="admin",
                    subscription_active=True,
                )
    except Exception:
        # Best-effort seeding; don't fail test collection if seeding fails.
        with __import__("contextlib").suppress(Exception):
            _ = None


@pytest.fixture(scope="session", autouse=True)
def seed_test_users(ensure_db_initialized) -> None:
    """Seed a small set of deterministic test user accounts used across tests.

    This is low-risk and idempotent: it uses the public `app.store` APIs
    (`get_user_by_email` and `create_user`) so we don't duplicate schema
    knowledge. It runs after `ensure_db_initialized` to ensure tables exist.
    """
    try:
        from app import store

        emails = [
            "test@example.com",
            "newuser@example.com",
            "pytest_test@example.com",
            "refreshuser@example.com",
            "refreshlogin@example.com",
            "rotuser@example.com",
            "revokeuser@example.com",
            "form_user@example.com",
        ]

        for e in emails:
            with __import__("contextlib").suppress(Exception):
                if not store.get_user_by_email(e):
                    # Create with minimal fields; password_hash may be None
                    store.create_user(email=e, password_hash=None, role="viewer")
    except Exception:
        # Best-effort; do not fail test collection if seeding fails.
        with __import__("contextlib").suppress(Exception):
            _ = None


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
            print(
                f"[conftest.ensure_per_test_sqlite_initialized] init returned {rc} for {url}"
            )
        # Also ensure the resolved `store.DB_PATH` file (if used directly by
        # tests) is initialized. This covers calls like
        # `sqlite3.connect(store.DB_PATH)` where DB_PATH may be a path-like.
        try:
            from app import store as _store

            resolved = str(_store.DB_PATH)
            if resolved and resolved != "":
                sqlite_url = f"sqlite:///{resolved}"
                rc2 = _init.main(sqlite_url)
                if rc2 != 0:
                    print(
                        f"[conftest.ensure_per_test_sqlite_initialized] init returned {rc2} for {sqlite_url}"
                    )
        except Exception:
            # Best-effort only; don't fail tests on logging issues.
            with __import__("contextlib").suppress(Exception):
                _ = None
    except Exception as exc:  # pragma: no cover - best-effort logging
        print(f"[conftest.ensure_per_test_sqlite_initialized] exception: {exc}")
        # Do not raise here; let tests fail on their own assertions.
