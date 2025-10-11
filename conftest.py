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


def _sqlite_url_for_path(path: str) -> str:
    """Return a sqlite URL suitable for the current platform for an absolute path.

    On Windows use three slashes with a drive letter (sqlite:///C:/path.db).
    On POSIX use four slashes to denote an absolute path (sqlite:////abs/path.db).
    """
    try:
        if os.name == "nt" or (len(path) > 1 and path[1] == ":"):
            # Normalize to forward slashes which SQLAlchemy accepts on Windows
            return "sqlite:///" + path.replace("\\", "/")
    except Exception:
        pass
    return "sqlite:////" + path.lstrip("/")


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
        # Use explicit absolute sqlite URL (four slashes) to ensure the
        # initializer writes to the exact filesystem path other code will
        # open (store.DB_PATH / sqlite3.connect()).
        try:
            _abs = str(_klerno_dbfile.resolve())
        except Exception:
            _abs = str(_klerno_dbfile)
        _klerno_url = _sqlite_url_for_path(_abs)
        # Force the env var so other modules import will see this DB URL
        os.environ["DATABASE_URL"] = _klerno_url
        # Also set DB_PATH env var to the absolute filesystem path so code that
        # opens sqlite directly using store.DB_PATH or os.getenv('DB_PATH') will
        # target the same file the initializer wrote to.
        try:
            os.environ["DB_PATH"] = str(Path(_klerno_dbfile).resolve())
        except Exception:
            os.environ["DB_PATH"] = str(_klerno_dbfile)
        # Mark that the import-time initializer created DB_PATH so later
        # fixtures can distinguish between an import-time created DB file
        # and a test-level fixture that intentionally set DB_PATH.
        os.environ.setdefault("KLERNO_PYTEST_IMPORT_DB", "1")
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
        # Construct an absolute sqlite URL so SQLAlchemy targets the same
        # filesystem file referenced by store.DB_PATH.
        try:
            _abs = str(dbfile.resolve())
        except Exception:
            _abs = str(dbfile)
        url = _sqlite_url_for_path(_abs)
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
    # If the test declares its own `test_db` fixture (legacy tests in
    # `tests/conftest.py` create a NamedTemporaryFile and set DATABASE_URL),
    # avoid overriding DATABASE_URL/DB_PATH here. That fixture intends to
    # control the DB the test uses; our autouse initializer would otherwise
    # point the app at a different sqlite file and break tests that write
    # directly to their `test_db`.
    if "test_db" in getattr(request, "fixturenames", []):
        # noop; let the test's `test_db` fixture control DATABASE_URL
        yield
        return

    # If a DB_PATH env var is already present (for example a session-scoped
    # `test_db` fixture wrote it), prefer that and do not create a per-test
    # sqlite file. This avoids races where the autouse initializer would
    # otherwise override a test's chosen DB file and cause schema/data
    # visibility mismatches.
    # Only skip autouse initialization when DB_PATH is present and it was
    # not created by our import-time helper. If DB_PATH was set by the
    # import-time initializer (KLERNO_PYTEST_IMPORT_DB=1), we should still
    # perform a per-test DB initialization so each test is isolated.
    if os.getenv("DB_PATH") and not os.getenv("KLERNO_PYTEST_IMPORT_DB"):
        yield
        return

    # Build a unique sqlite path per test
    test_name = request.node.name
    # Keep names filesystem-safe by using the node id hash if necessary
    dbfile = tmp_path / f"{test_name}.db"
    # Resolve absolute filesystem path and construct a sqlite URL that
    # unambiguously targets that file (use four slashes for absolute paths).
    try:
        abs_path = str(dbfile.resolve())
    except Exception:
        abs_path = str(dbfile)
    url = _sqlite_url_for_path(abs_path)
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
    # created. Use the previously-computed abs_path to guarantee consistency.
    try:
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
        # Call initializer against the explicit absolute URL we constructed
        _init_main(url)
        try:
            # We already have the absolute filesystem path in `abs_path`.
            db_path = abs_path
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
            # Treat the ASGI test host ('test') as local as well so our stub
            # doesn't intercept in-process ASGITransport requests used by tests.
            if host and host not in {"test", "testserver", "127.0.0.1", "localhost"}:
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
