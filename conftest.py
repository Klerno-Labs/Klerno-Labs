"""Top-level pytest configuration.

Placing pytest_plugins here avoids the deprecation warning when other
conftest files live in subpackages (like CLEAN_APP/tests). Tests expect
the asyncio plugin; declare it once at the repository root.
"""

import contextlib
import os
import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

import app.store as store

pytest_plugins = ["asyncio"]


# Create a session-level sqlite DB as early as possible (module import time)
# so tests that import the application and create a TestClient at import
# time won't trigger import-time DB access against a non-initialized DB.
# We only do this when DATABASE_URL is not already set in the environment
# to avoid clobbering intentionally provided DB settings.
_klerno_pytest_session_tmpdir: str | None = None
if not os.getenv("DATABASE_URL"):
    try:
        _klerno_pytest_session_tmpdir = tempfile.mkdtemp(
            prefix="klerno_pytest_session_"
        )
        _klerno_dbfile = Path(_klerno_pytest_session_tmpdir) / "klerno_session.db"
        _klerno_url = f"sqlite:///{_klerno_dbfile}"
        # Force the env var so other modules import will see this DB URL
        os.environ["DATABASE_URL"] = _klerno_url
        # Also set DB_PATH env var to the absolute filesystem path so code that
        # opens sqlite directly using store.DB_PATH or os.getenv('DB_PATH') will
        # target the same file the initializer wrote to.
        try:
            os.environ["DB_PATH"] = str(Path(_klerno_dbfile).resolve())
        except Exception:
            os.environ["DB_PATH"] = str(_klerno_dbfile)
        try:
            store.DATABASE_URL = os.getenv("DATABASE_URL") or ""
        except Exception:
            pass
        # Initialize schema using canonical initializer; ignore failures
        try:
            from scripts.init_db_if_needed import main as _init_main

            _init_main(_klerno_url)
        except Exception:
            pass
    except Exception:
        _klerno_pytest_session_tmpdir = None


def pytest_configure(config) -> None:
    """Prepare a session-level sqlite DB so import-time app code finds tables.

    This runs before collection and ensures modules that access the DB at
    import-time won't see a missing schema. We create a temporary DB file and
    call the canonical initializer. The per-test fixture still provides fresh
    sqlite DBs for test isolation, but this session DB prevents import-time
    race conditions in CI.
    """
    try:
        tmpdir = tempfile.mkdtemp(prefix="klerno_pytest_session_")
        dbfile = Path(tmpdir) / "klerno_session.db"
        url = f"sqlite:///{dbfile}"
        os.environ.setdefault("DATABASE_URL", url)
        # Mirror the environment selection on the store module so module-
        # level constants reflect the runtime DB used by the initializer.
        try:
            store.DATABASE_URL = os.getenv("DATABASE_URL") or ""
        except Exception:
            pass
        # Call canonical initializer; ignore errors so pytest can proceed
        from scripts.init_db_if_needed import main as _init_main

        _init_main(url)
        # store tmpdir for cleanup
        config.klerno_pytest_tmpdir = tmpdir
    except Exception:
        # best-effort; let tests fail later if something else breaks
        pass


def pytest_unconfigure(config) -> None:
    """Cleanup the temporary session DB directory created in pytest_configure."""
    try:
        tmpdir = getattr(config, "klerno_pytest_tmpdir", None)
        if tmpdir and Path(tmpdir).is_dir():
            shutil.rmtree(tmpdir, ignore_errors=True)
        # Also cleanup the module-level tmpdir if we created one at import time
        try:
            global _klerno_pytest_session_tmpdir
            if (
                _klerno_pytest_session_tmpdir
                and Path(_klerno_pytest_session_tmpdir).is_dir()
            ):
                shutil.rmtree(_klerno_pytest_session_tmpdir, ignore_errors=True)
                _klerno_pytest_session_tmpdir = None
        except Exception:
            pass
    except Exception:
        pass


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
    # Also update store module-level DATABASE_URL so import-time values
    # align with the per-test env override (helps modules that read the
    # module-global value instead of os.getenv at call time).
    try:
        store.DATABASE_URL = url
    except Exception:
        pass

    # Export DB_PATH as an absolute filesystem path so direct sqlite.connect
    # calls (or code that reads DB_PATH env) use the same file the initializer
    # created. Use resolve() to normalize symlinks/relative fragments.
    try:
        abs_path = str(Path(dbfile).resolve())
        monkeypatch.setenv("DB_PATH", abs_path)
        os.environ["DB_PATH"] = abs_path
    except Exception:
        try:
            monkeypatch.setenv("DB_PATH", str(dbfile))
            os.environ["DB_PATH"] = str(dbfile)
        except Exception:
            pass

    # Call the canonical initializer from scripts/init_db_if_needed.py
    try:
        from scripts.init_db_if_needed import main as _init_main

        # Call initializer and verify expected tables exist. Some CI environments
        # show intermittent races where create_all() returns before the test's
        # sqlite connection sees the tables. Retry a few times to make this
        # robust while keeping the change low-risk.
        _init_main(url)
        try:
            # Compute filesystem path from sqlite URL (preserve leading slash semantics)
            raw = url.split("sqlite://", 1)[1]
            db_path = (
                "/" + raw.lstrip("/") if raw.startswith("////") else raw.lstrip("/")
            )
            # Relaxed verification: ensure core tables are present
            import sqlite3
            import time

            def _has_tables(path, tables=("users", "txs")) -> bool:
                try:
                    con = sqlite3.connect(path)
                    cur = con.cursor()
                    for t in tables:
                        cur.execute(
                            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                            (t,),
                        )
                        if cur.fetchone() is None:
                            return False
                    return True
                except Exception:
                    return False

            tries = 0
            while tries < 3 and not _has_tables(db_path):
                # Small backoff and attempt to initialize again
                time.sleep(0.05 * (tries + 1))
                _init_main(url)
                tries += 1
        except Exception:
            # Best-effort verification; do not hard-fail here to keep fixture low-risk
            pass
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


@pytest.fixture(scope="session", autouse=True)
def stub_neon_data_api(request) -> None:
    """Stub outbound Neon Data API calls made via httpx so CI doesn't need network.

    This session-scoped fixture avoids depending on the function-scoped
    `monkeypatch` fixture by doing a manual attribute swap on
    httpx.AsyncClient.send and registering a finalizer to restore it.
    """
    try:
        import httpx
        from httpx import Request, Response

        async def _fake_send(self, request: Request, *args, **kwargs):
            url = str(request.url)
            # Minimal stubs for common Neon endpoints used in tests.
            # Support both the proxied routes (e.g. /api/neon/notes) and the
            # Data API paths (e.g. /rest/v1/notes) the app may call directly.

            def _ok_json(obj):
                return Response(200, json=obj)

            # Simple auth simulation: if Authorization header missing and
            # NEON_API_KEY env not set, return 401 for protected endpoints.
            auth_header = request.headers.get("authorization")
            neon_key_env = os.getenv("NEON_API_KEY")

            def _requires_auth():
                return not (auth_header or neon_key_env)

            if "/api/neon/notes" in url or "/rest/v1/notes" in url:
                if _requires_auth():
                    return Response(401, json={"message": "Unauthorized"})
                # Return a PostgREST-style list of rows (empty by default)
                return _ok_json([])
            if "/api/neon/paragraphs" in url or "/rest/v1/paragraphs" in url:
                if _requires_auth():
                    return Response(401, json={"message": "Unauthorized"})
                return _ok_json([])
            # Generic Neon proxy endpoints under /api/neon may expect simple JSON
            if "/api/neon/" in url:
                return _ok_json({})
            # Fallback: call original send if present, otherwise return 502
            # If the request is going to an external host (not testserver),
            # avoid real network calls in CI by returning a safe default JSON
            # response. This prevents httpcore ConnectError and empty bodies
            # which caused json.decoder.JSONDecodeError in CI logs.
            try:
                host = request.url.host or ""
            except Exception:
                host = ""
            if host and host not in {"testserver", "127.0.0.1", "localhost"}:
                # If the endpoint expects auth, simulate 401 when missing
                if _requires_auth():
                    return Response(401, json={"message": "Unauthorized"})
                # Return an empty but valid JSON object for external calls
                return Response(200, json={})

            if _orig_send is None:
                return Response(502, json={})
            return await _orig_send(self, request, *args, **kwargs)

        # Save original and replace
        _orig_send = getattr(httpx.AsyncClient, "send", None)
        try:
            httpx.AsyncClient.send = _fake_send  # direct assignment is fine here
        except Exception:
            # best-effort; if we can't set it, continue without stub
            return

        # Register finalizer to restore original behavior at session end
        def _restore():
            if _orig_send is None:
                with contextlib.suppress(Exception):
                    delattr(httpx.AsyncClient, "send")
            else:
                httpx.AsyncClient.send = _orig_send

        request.addfinalizer(_restore)
    except Exception:
        # If httpx isn't importable or another error occurs, skip stubbing.
        pass
