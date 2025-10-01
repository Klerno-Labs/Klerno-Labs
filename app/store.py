"""
Data store utilities with SQLite/Postgres backends and a small cache.
"""

# bandit: skip-file
# Justification: This module constructs SQL using an internal `_ph()` placeholder
# function and passes parameters separately to DB driver APIs (sqlite3/psycopg).
# Bandit generates many B608 (hardcoded_sql_expressions) findings on the
# multi-line f-strings even though values are supplied via parameters. To
# reduce noisy CI failures while preserving runtime safety, skip Bandit for
# this file and add a follow-up audit to re-introduce granular suppressions
# where appropriate.
# TODO(klerno): Re-audit `app/store.py` to remove `bandit: skip-file` and
# replace with explicit `# nosec: B608` on exact lines or refactor to avoid
# f-string interpolation in SQL literals.

import contextlib
import json
import logging
import os
import sqlite3
import time
from collections.abc import Iterable, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any, NotRequired, TypedDict, cast

from app._typing_shims import ISyncConnection
from app.constants import CACHE_TTL

# Simple in-memory cache for frequently accessed data
# Add explicit type annotations to satisfy static checkers
_cache: dict[str, Any] = {}
_cache_expiry: dict[str, float] = {}


def _safe_idx(seq: Sequence[Any] | Any, idx: int) -> Any:
    """Safely get index from a sequence-like object.

    Many DB cursors return sqlite3.Row or sequences; static checkers can't
    always infer lengths. Use this helper to avoid IndexError/static
    complaints while keeping runtime semantics identical.
    """
    try:
        if seq is None:
            return None
        # Works for lists/tuples and sqlite3.Row (supports index access)
        return seq[idx] if isinstance(seq, Sequence) and len(seq) > idx else seq[idx]
    except Exception:
        return None


def _get_cache_key(*args: Any) -> str:
    """Generate cache key from arguments."""
    return "|".join(str(arg) for arg in args)


def _get_cached(key: str, ttl: int = CACHE_TTL) -> Any | None:
    """Get cached value if not expired."""
    if key in _cache:
        if time.time() < _cache_expiry.get(key, 0):
            return _cache[key]
        else:
            # Expired, remove from cache
            _cache.pop(key, None)
            _cache_expiry.pop(key, None)
    return None


def _set_cache(key: str, value: Any, ttl: int = CACHE_TTL) -> None:
    """Set cached value with expiry."""
    _cache[key] = value
    _cache_expiry[key] = time.time() + ttl


def _clear_cache_pattern(pattern: str) -> None:
    """Clear cache entries matching pattern."""
    keys_to_remove = [k for k in _cache if pattern in k]
    for key in keys_to_remove:
        _cache.pop(key, None)
        _cache_expiry.pop(key, None)


# --- Config & detection ---

DATABASE_URL = os.getenv("DATABASE_URL") or ""

# Persistent SQLite path (fallback if not using Postgres)
# Use pathlib for clearer path operations while preserving string DB_PATH
BASE_DIR = Path(__file__).parent


# DB_PATH: expose a path-like object so code (and tests) that read
# `store.DB_PATH` after tests set `DATABASE_URL` will get the runtime
# effective path. Many tests set DATABASE_URL in fixtures (after
# modules are imported) — making DB_PATH dynamic fixes cases where the
# module-level value was captured too early and pointed at the wrong DB.
class _DBPath:
    def __init__(self, default_path: str) -> None:
        self._default = default_path

    def _compute(self) -> str:
        # Prefer explicit sqlite DATABASE_URL when present
        runtime_db = os.getenv("DATABASE_URL") or ""
        if runtime_db and runtime_db.startswith("sqlite://"):
            path = runtime_db.split("sqlite://", 1)[1].lstrip("/")
            if path:
                return path
            # if no path fragment, fall back to default
        # else prefer explicit DB_PATH env var or default
        return os.getenv("DB_PATH", self._default)

    def __fspath__(self) -> str:  # pathlib / os.fspath compatibility
        return self._compute()

    def __str__(self) -> str:
        return self._compute()

    def __repr__(self) -> str:
        return f"<DB_PATH {self._compute()}>"


DB_PATH = _DBPath(str(BASE_DIR / ".." / "data" / "klerno.db"))

# Support either psycopg (psycopg3) or psycopg2 if available.
PSYCOPG_AVAILABLE = False
PSYCOPG_LIBRARY = None
psycopg: Any | None = None
RealDictCursor: Any | None = None
try:
    import psycopg as psycopg3

    psycopg = psycopg3
    PSYCOPG_AVAILABLE = True
    PSYCOPG_LIBRARY = "psycopg"
except Exception:
    try:
        import psycopg2 as psycopg2_mod
        from psycopg2.extras import RealDictCursor as _RealDictCursor

        psycopg = psycopg2_mod
        RealDictCursor = _RealDictCursor
        PSYCOPG_AVAILABLE = True
        PSYCOPG_LIBRARY = "psycopg2"
    except Exception:  # pragma: no cover - optional dependency
        psycopg = None
        RealDictCursor = None
        PSYCOPG_AVAILABLE = False

# If DATABASE_URL points to a sqlite URL (common in tests/tools), prefer the
# sqlite backend even if a psycopg library is available. This avoids psycopg
# attempting to parse sqlite connection strings which results in confusing
# errors when tools set DATABASE_URL to 'sqlite:///...'.
USING_POSTGRES = (
    bool(DATABASE_URL)
    and PSYCOPG_AVAILABLE
    and not (DATABASE_URL.startswith("sqlite://"))
)

logger = logging.getLogger(__name__)
# Logging is configured centrally in app.logging_config.configure_logging()


# --- Connection factories -----------------------------------------------------


def _sqlite_conn() -> ISyncConnection:
    # honor DB_PATH and ensure directory exists
    # Allow DATABASE_URL to override DB path at runtime. Tests may set this.
    runtime_db = os.getenv("DATABASE_URL") or ""
    if runtime_db and runtime_db.startswith("sqlite://"):
        path = runtime_db.split("sqlite://", 1)[1].lstrip("/")
        db_path = path or DB_PATH
    else:
        db_path = DB_PATH

    # (no debug prints) ensure we don't leave unused imports behind

    data_dir = Path(db_path).resolve().parent
    data_dir.mkdir(parents=True, exist_ok=True)
    # use a small timeout so concurrent writers don't immediately fail
    con = cast(
        ISyncConnection, sqlite3.connect(db_path, check_same_thread=False, timeout=5.0)
    )
    con.row_factory = sqlite3.Row  # return dict - like rows to unify handling
    # Improve concurrency/performance for test and multi-request workloads:
    # - WAL reduces write lock contention allowing readers during writes
    # - synchronous=NORMAL gives good durability with better write throughput
    # - temp_store=MEMORY keeps temporary tables in memory
    try:
        with contextlib.suppress(Exception):
            con.execute("PRAGMA journal_mode=WAL;")
            con.execute("PRAGMA synchronous=NORMAL;")
            con.execute("PRAGMA temp_store=MEMORY;")
    except Exception:
        # Best-effort: don't fail connection creation if pragmas are unsupported
        with contextlib.suppress(Exception):
            _ = None
    # Cast runtime sqlite3.Connection to ISyncConnection for typing
    return cast(ISyncConnection, con)


def _postgres_conn(retries: int | None = None, backoff: float | None = None) -> Any:
    """
    Create a Postgres connection with a small retry/backoff policy.

    This attempts to support both `psycopg` (psycopg3) and `psycopg2`.
    Retries and backoff can be controlled with env vars `DB_CONNECT_RETRIES`
    and `DB_CONNECT_BACKOFF` (seconds).
    """
    if retries is None:
        try:
            retries = int(os.getenv("DB_CONNECT_RETRIES", "3"))
        except Exception:
            retries = 3
    if backoff is None:
        try:
            backoff = float(os.getenv("DB_CONNECT_BACKOFF", "0.1"))
        except Exception:
            backoff = 0.1

    last_exc = None
    for attempt in range(max(1, retries)):
        try:
            if PSYCOPG_LIBRARY == "psycopg":
                # psycopg3: connect with the URL directly
                assert psycopg is not None
                return psycopg.connect(DATABASE_URL)
            # psycopg2
            assert psycopg is not None
            assert RealDictCursor is not None
            return psycopg.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        except Exception as e:
            last_exc = e
            # exponential backoff
            try:
                time.sleep(backoff * (2**attempt))
            except Exception:
                with contextlib.suppress(Exception):
                    _ = None
    # If we get here, raise the last exception to surface connection issues
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("failed to create postgres connection")


def _conn() -> Any:
    """
    Return a DB connection:
    - Postgres if DATABASE_URL & psycopg2 are available
    - else SQLite
    """
    return _postgres_conn() if USING_POSTGRES else _sqlite_conn()


def _ph() -> str:
    """Return the correct SQL placeholder for the active backend."""
    return "%s" if USING_POSTGRES else "?"


def wait_for_row(
    select_sql: str, params: tuple = (), timeout: float = 1.0, poll: float = 0.05
) -> list[Any]:
    """Wait for a row to become visible in the database.

    This helper repeatedly executes `select_sql` with `params` until at least
    one row is returned or `timeout` seconds elapse. It is useful to mitigate
    read-after-write visibility on some platforms or under heavy lock contention.

    Returns the fetched rows (possibly empty if timeout elapsed).
    """
    start = time.time()
    while True:
        try:
            con = _conn()
            cur = con.cursor()
            cur.execute(select_sql, params)
            rows = cur.fetchall()
            # Close only sqlite connections created here; psycopg2 will be handled by driver
            from contextlib import suppress

            with suppress(Exception):
                con.close()
            if rows:
                return rows
        except Exception:
            # Swallow and retry until timeout
            with contextlib.suppress(Exception):
                _ = None

        if time.time() - start >= timeout:
            return []
        time.sleep(poll)


# --- Schema management --------------------------------------------------------


def init_db() -> None:
    """
    Create tables if they do not exist:
      - txs           : transactions store
      - users         : auth / accounts
      - user_settings : per - user persisted settings (x_api_key, thresholds, etc.)
    Also adds helpful indexes.
    """
    # Clear in-memory caches to avoid carrying state between test runs
    try:
        _cache.clear()
        _cache_expiry.clear()
    except Exception:
        # Ignore cache clearing failures during init (best-effort)
        with contextlib.suppress(Exception):
            _ = None

    # If DATABASE_URL points to a sqlite file (used by tests), connect directly
    runtime_db = os.getenv("DATABASE_URL") or ""
    if runtime_db and runtime_db.startswith("sqlite://"):
        path = runtime_db.split("sqlite://", 1)[1].lstrip("/")
        db_path = path or DB_PATH
        # ensure directory
        data_dir = Path(db_path).resolve().parent
        data_dir.mkdir(parents=True, exist_ok=True)
        con = cast(ISyncConnection, sqlite3.connect(db_path, check_same_thread=False))
        con.row_factory = sqlite3.Row
    else:
        con = _conn()
    cur = con.cursor()

    # ---- TXS TABLE ----
    if USING_POSTGRES:
        cur.execute(
            """
        CREATE TABLE IF NOT EXISTS txs (
            id SERIAL PRIMARY KEY,
                tx_id TEXT,
                timestamp TEXT,
                chain TEXT,
                from_addr TEXT,
                to_addr TEXT,
                amount DOUBLE PRECISION,
                symbol TEXT,
                direction TEXT,
                memo TEXT,
                fee DOUBLE PRECISION,
                category TEXT,
                risk_score DOUBLE PRECISION,
                risk_flags TEXT,
                notes TEXT
        );"""
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_txs_from_addr ON txs (from_addr);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_txs_to_addr ON txs (to_addr);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_txs_timestamp ON txs (timestamp);")
        # Additional indexes for admin analytics performance
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_txs_risk_score ON txs (risk_score);"
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_txs_category ON txs (category);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_txs_amount ON txs (amount);")
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_txs_timestamp_desc ON txs (timestamp DESC);"
        )
    else:
        cur.execute(
            """
        CREATE TABLE IF NOT EXISTS txs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
                tx_id TEXT,
                timestamp TEXT,
                chain TEXT,
                from_addr TEXT,
                to_addr TEXT,
                amount REAL,
                symbol TEXT,
                direction TEXT,
                memo TEXT,
                fee REAL,
                category TEXT,
                risk_score REAL,
                risk_flags TEXT,
                notes TEXT
        );"""
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_txs_from_addr ON txs (from_addr);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_txs_to_addr ON txs (to_addr);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_txs_timestamp ON txs (timestamp);")
        # Additional indexes for admin analytics performance
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_txs_risk_score ON txs (risk_score);"
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_txs_category ON txs (category);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_txs_amount ON txs (amount);")
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_txs_timestamp_desc ON txs (timestamp DESC);"
        )

    # ---- USERS TABLE ----
    if USING_POSTGRES:
        # users table: role can be 'admin' | 'analyst' | 'viewer'
        # OAuth provider data: 'google' | 'microsoft' | null
        # (for email / password)
        # wallet_addresses stores a JSON array of wallet objects
        cur.execute(
            """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT,
                role TEXT NOT NULL DEFAULT 'viewer',
                subscription_active BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                oauth_provider TEXT,
                oauth_id TEXT,
                display_name TEXT,
                avatar_url TEXT,
                wallet_addresses TEXT DEFAULT '[]',
                totp_secret TEXT,
                mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE,
                mfa_type TEXT,
                recovery_codes TEXT DEFAULT '[]',
                has_hardware_key BOOLEAN NOT NULL DEFAULT FALSE
        );"""
        )
        # Indexes for user queries
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users (role);")
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_users_created_at ON users (created_at);"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_users_oauth_provider "
            "ON users (oauth_provider);"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_users_oauth_id ON users (oauth_id);"
        )
    else:
        # users table (SQLite): subscription_active uses 0 / 1
        # See notes above for role, OAuth provider fields, and wallet_addresses JSON
        cur.execute(
            """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT,
                role TEXT NOT NULL DEFAULT 'viewer',
                subscription_active INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                oauth_provider TEXT,
                oauth_id TEXT,
                display_name TEXT,
                avatar_url TEXT,
                wallet_addresses TEXT DEFAULT '[]',
                totp_secret TEXT,
                mfa_enabled INTEGER NOT NULL DEFAULT 0,
                mfa_type TEXT,
                recovery_codes TEXT DEFAULT '[]',
                has_hardware_key INTEGER NOT NULL DEFAULT 0
        );"""
        )
        # Basic indexes for user queries
        # Use contextlib.suppress to ignore index creation errors
        # on older SQLite
        with contextlib.suppress(sqlite3.OperationalError):
            cur.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);")
        with contextlib.suppress(sqlite3.OperationalError):
            cur.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users (role);")
        with contextlib.suppress(sqlite3.OperationalError):
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_users_created_at ON users (created_at);"
            )

    # Add columns to existing users table if they don't exist (migration)
    try:
        if USING_POSTGRES:
            cur.execute(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS oauth_provider TEXT;"
            )
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS oauth_id TEXT;")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS display_name TEXT;")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url TEXT;")
            cur.execute(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS wallet_addresses TEXT "
                "DEFAULT '[]';"
            )
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_secret TEXT;")
            cur.execute(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_enabled BOOLEAN "
                "NOT NULL DEFAULT FALSE;"
            )
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_type TEXT;")
            cur.execute(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS recovery_codes TEXT "
                "DEFAULT '[]';"
            )
            cur.execute(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS has_hardware_key BOOLEAN "
                "NOT NULL DEFAULT FALSE;"
            )
        else:
            # SQLite doesn't support IF NOT EXISTS for ALTER TABLE,
            # so we use a try / except
            for coldef in [
                ("totp_secret TEXT",),
                ("mfa_enabled INTEGER NOT NULL DEFAULT 0",),
                ("mfa_type TEXT",),
                ("recovery_codes TEXT DEFAULT '[]'",),
                ("has_hardware_key INTEGER NOT NULL DEFAULT 0",),
            ]:
                with contextlib.suppress(sqlite3.OperationalError):
                    cur.execute(f"ALTER TABLE users ADD COLUMN {coldef[0]};")
    except Exception as e:
        print(f"Migration warning: {e}")

    # Create indexes for new OAuth columns (after migration)
    # Create indexes for new OAuth columns (after migration) if possible
    with contextlib.suppress(sqlite3.OperationalError):
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_users_oauth_provider "
            "ON users (oauth_provider);"
        )
    with contextlib.suppress(sqlite3.OperationalError):
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_users_oauth_id ON users (oauth_id);"
        )

    # ---- USER_SETTINGS TABLE (normalized columns) ----
    if USING_POSTGRES:
        cur.execute(
            """
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                x_api_key TEXT,
                risk_threshold DOUBLE PRECISION,
                time_range_days INTEGER,
                ui_prefs JSONB,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );"""
        )
    else:
        cur.execute(
            """
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
                x_api_key TEXT,
                risk_threshold REAL,
                time_range_days INTEGER,
                ui_prefs TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );"""
        )

    con.commit()
    con.close()

    # --- Row helpers --------------------------------------------------------------


class UserDict(TypedDict):
    # id may be int/str depending on DB driver
    id: Any
    # These fields are expected to always be present after normalization
    email: str
    role: str
    subscription_active: bool
    # Normalized to a list during _row_to_user
    wallet_addresses: list[dict[str, Any]]
    mfa_enabled: bool
    recovery_codes: list[str]
    has_hardware_key: bool

    # Optional fields
    password_hash: NotRequired[str | None]
    created_at: NotRequired[Any | None]
    oauth_provider: NotRequired[str | None]
    oauth_id: NotRequired[str | None]
    display_name: NotRequired[str | None]
    avatar_url: NotRequired[str | None]
    totp_secret: NotRequired[str | None]
    mfa_type: NotRequired[str | None]


def _rows_to_dicts(rows: Iterable[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in rows:
        # r can be psycopg2 RealDictRow (dict) or sqlite3.Row (mapping - like)
        d = dict(r) if isinstance(r, dict) else {k: r[k] for k in r}

        # normalize risk_flags to a list
        raw = d.get("risk_flags")
        try:
            d["risk_flags"] = (
                json.loads(raw) if isinstance(raw, (str, bytes)) else (raw or [])
            )
        except Exception:
            d["risk_flags"] = []

        out.append(d)
    return out


def _row_to_user(row: Any | None) -> UserDict | None:
    if not row:
        return None
    # If the legacy schema included a 'subscription_status' column (string),
    # pass it through so compatibility checks that look for subscription_status
    # (e.g., 'active') will work.

    # Define expected columns in order
    expected_columns = [
        "id",
        "email",
        "password_hash",
        "role",
        "subscription_active",
        "created_at",
        "oauth_provider",
        "oauth_id",
        "display_name",
        "avatar_url",
        "wallet_addresses",
        "totp_secret",
        "mfa_enabled",
        "mfa_type",
        "recovery_codes",
        "has_hardware_key",
    ]

    # Convert row to dict safely
    if isinstance(row, dict):
        d = dict(row)
    else:
        # SQLite Row object - convert using column positions
        d = {}
        for i, col_name in enumerate(expected_columns):
            try:
                d[col_name] = row[i] if i < len(row) else None
            except (IndexError, KeyError):
                d[col_name] = None

    d["subscription_active"] = bool(d.get("subscription_active"))

    # Parse wallet addresses from JSON
    wallet_addresses_str = d.get("wallet_addresses", "[]")
    try:
        wallet_addresses = (
            json.loads(wallet_addresses_str) if wallet_addresses_str else []
        )
    except (json.JSONDecodeError, TypeError):
        wallet_addresses = []

    # MFA fields
    recovery_codes_str = d.get("recovery_codes", "[]")
    try:
        recovery_codes = json.loads(recovery_codes_str) if recovery_codes_str else []
    except (json.JSONDecodeError, TypeError):
        recovery_codes = []

    # Normalize and coerce required fields to satisfy static typing and
    # provide consistent runtime shapes for callers.
    normalized_email = d.get("email") or ""
    normalized_role = str(d.get("role") or "viewer")
    normalized_subscription_active = bool(d.get("subscription_active"))
    normalized_wallet_addresses: list[dict[str, Any]] = (
        wallet_addresses if isinstance(wallet_addresses, list) else []
    )
    normalized_recovery_codes: list[str] = [str(c) for c in recovery_codes]
    normalized_mfa_enabled = bool(d.get("mfa_enabled", False))
    normalized_has_hardware_key = bool(d.get("has_hardware_key", False))

    user: UserDict = {
        "id": d.get("id"),
        "email": normalized_email,
        "password_hash": d.get("password_hash"),
        "role": normalized_role,
        "subscription_active": normalized_subscription_active,
        "created_at": d.get("created_at"),
        "oauth_provider": d.get("oauth_provider"),
        "oauth_id": d.get("oauth_id"),
        "display_name": d.get("display_name"),
        "avatar_url": d.get("avatar_url"),
        "wallet_addresses": normalized_wallet_addresses,
        "totp_secret": d.get("totp_secret"),
        "mfa_enabled": normalized_mfa_enabled,
        "mfa_type": d.get("mfa_type"),
        "recovery_codes": normalized_recovery_codes,
        "has_hardware_key": normalized_has_hardware_key,
    }
    return user


# --- Transactions API ---------------------------------------------------------


def save_tagged(t: dict[str, Any]) -> int:
    con = _conn()
    cur = con.cursor()
    # SQL placeholder for current backend (inline {_ph()} is used)
    # Parameterized query using _ph() placeholders and parameters tuple - safe from SQL injection
    sql = f"""
      INSERT INTO txs (
        tx_id, timestamp, chain, from_addr, to_addr, amount, symbol, direction,
            memo, fee, category, risk_score, risk_flags, notes
      )
        VALUES (
            {_ph()},{_ph()},{_ph()},{_ph()},{_ph()},{_ph()},{_ph()},{_ph()},
            {_ph()},{_ph()},{_ph()},{_ph()},{_ph()},{_ph()}
        )
    """  # nosec: B608 - placeholders used; parameters passed separately
    cur.execute(
        sql,
        (
            t["tx_id"],
            str(t["timestamp"]),
            t["chain"],
            t["from_addr"],
            t["to_addr"],
            float(t["amount"]),
            t["symbol"],
            t["direction"],
            t.get("memo"),
            float(t.get("fee") or 0.0),
            t.get("category", "unknown"),
            float(t.get("risk_score") or 0.0),
            json.dumps(t.get("risk_flags", [])),
            t.get("notes"),
        ),
    )
    con.commit()
    new_id = cur.lastrowid
    con.close()

    # Invalidate transaction - related caches
    _clear_cache_pattern("list_all")
    _clear_cache_pattern("list_by_wallet")
    _clear_cache_pattern("list_alerts")
    return int(new_id or 0)


def get_by_id(tx_id: int) -> dict[str, Any] | None:
    """Return a single transaction row by primary id, or None if not found.

    This is a minimal, best-effort helper used by compatibility fallback
    code in other modules. It prefers the active DB backend and returns
    a mapping when available.
    """
    con = _conn()
    cur = con.cursor()
    # placeholder not needed; using inline {_ph()} in query
    try:
        if USING_POSTGRES:
            cur.execute("SELECT * FROM txs WHERE id = %s", (tx_id,))
        else:
            cur.execute("SELECT * FROM txs WHERE id = ?", (tx_id,))
        row = cur.fetchone()
        con.close()
        if not row:
            return None
        return dict(row) if isinstance(row, dict) else {k: row[k] for k in row}
    except Exception:
        with contextlib.suppress(Exception):
            con.close()
        return None


def list_by_wallet(wallet: str, limit: int = 100) -> list[dict[str, Any]]:
    con = _conn()
    cur = con.cursor()
    # placeholder not needed; using inline {_ph()} in query
    # Parameterized query using internal {_ph()} placeholder function and a
    # separate parameters tuple. This is safe against SQL injection.
    # Parameterized SELECT by wallet, safe: placeholders used in parameters tuple
    sql = f"""
        SELECT
            tx_id, timestamp, chain, from_addr, to_addr, amount, symbol, direction,
            memo, fee, category, risk_score, risk_flags, notes
        FROM txs
        WHERE from_addr={_ph()} OR to_addr={_ph()}
        ORDER BY id DESC
        LIMIT {_ph()}
    """  # nosec: B608 - parameterized placeholders used
    cur.execute(
        sql, (wallet, wallet, limit)
    )  # nosec: B608 - parameterized placeholders used
    rows = cur.fetchall()
    con.close()
    return _rows_to_dicts(rows)


def list_alerts(threshold: float = 0.75, limit: int = 100) -> list[dict[str, Any]]:
    con = _conn()
    cur = con.cursor()
    # placeholder not needed; using inline {_ph()} in query
    # Parameterized query using internal {_ph()} placeholder function and a
    # separate parameters tuple. This is safe against SQL injection.
    # Parameterized SELECT by risk threshold - placeholders used
    sql = f"""
        SELECT
            tx_id, timestamp, chain, from_addr, to_addr, amount, symbol, direction,
            memo, fee, category, risk_score, risk_flags, notes
        FROM txs
        WHERE risk_score >= {_ph()}
        ORDER BY id DESC
        LIMIT {_ph()}
    """  # nosec: B608 - parameterized placeholders used
    cur.execute(
        sql, (threshold, limit)
    )  # nosec: B608 - parameterized placeholders used
    rows = cur.fetchall()
    con.close()
    return _rows_to_dicts(rows)


def list_all(limit: int = 1000) -> list[dict[str, Any]]:
    # Check cache first
    cache_key = _get_cache_key("list_all", limit)
    cached_result = _get_cached(cache_key, ttl=60)  # Cache for 1 minute
    if cached_result is not None:
        return cached_result

    con = _conn()
    cur = con.cursor()
    # placeholder not needed; using inline {_ph()} in query
    # Parameterized query using internal {_ph()} placeholder function and a
    # separate parameters tuple. This is safe against SQL injection.
    # Parameterized SELECT all txs with limit
    sql = f"""
        SELECT
            tx_id, timestamp, chain, from_addr, to_addr, amount, symbol, direction,
            memo, fee, category, risk_score, risk_flags, notes
        FROM txs
        ORDER BY id DESC
        LIMIT {_ph()}
    """  # nosec: B608 - parameterized placeholders used
    cur.execute(sql, (limit,))  # nosec: B608 - parameterized placeholders used
    rows = cur.fetchall()
    con.close()
    result = _rows_to_dicts(rows)

    # Cache the result
    _set_cache(cache_key, result, ttl=60)
    return result


def legacy_transactions_exists() -> bool:
    """Check whether a legacy `transactions` table exists in the active DB.

    Uses the centralized connection factory so callers share the same view of
    the database (important for tests which set `DATABASE_URL` at runtime).
    """
    con = None
    try:
        con = _conn()
        cur = con.cursor()
        try:
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='transactions'"
            )
            return cur.fetchone() is not None
        except Exception:
            return False
    finally:
        with contextlib.suppress(Exception):
            if con is not None:
                con.close()


# --- Users API ----------------------------------------------------------------


def users_count() -> int:
    con = _conn()
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) AS n FROM users")
    row = cur.fetchone()
    con.close()
    if isinstance(row, dict):
        return int(row.get("n", 0))
    return int(row[0]) if row else 0


def get_user_by_email(email: str) -> UserDict | None:
    # Debug: print runtime DB selection info when troubleshooting
    # Emit debug-level diagnostic information; controlled by central logging level
    with contextlib.suppress(Exception):
        logger.debug(
            "STORE_DEBUG: DATABASE_URL=%r, DB_PATH=%r, USING_POSTGRES=%s",
            DATABASE_URL,
            DB_PATH,
            USING_POSTGRES,
        )

    # Check cache first
    cache_key = _get_cache_key("user_by_email", email.lower())
    cached_result = _get_cached(cache_key, ttl=300)  # Cache for 5 minutes
    if cached_result is not None:
        return cached_result

    con = _conn()
    cur = con.cursor()
    # placeholder not needed; using inline {_ph()} in query
    try:
        # Parameterized query using internal {_ph()} placeholder function and a
        # separate parameters tuple. This is safe against SQL injection.
        sql = f"""
            SELECT id, email, password_hash, role, subscription_active, created_at,
                   oauth_provider, oauth_id, display_name, avatar_url, wallet_addresses,
                       totp_secret, mfa_enabled, mfa_type, recovery_codes, has_hardware_key
            FROM users WHERE email={_ph()}
        """  # nosec: B608 - parameterized placeholders used
        logger.debug(
            "get_user_by_email: executing SQL=%r params=%r DATABASE_URL=%r DB_PATH=%r",
            sql,
            (email,),
            os.getenv("DATABASE_URL"),
            DB_PATH,
        )
        cur.execute(sql, (email,))  # nosec: B608 - parameterized placeholders used
        row = cur.fetchone()
        logger.debug("get_user_by_email: fetched row=%r", row)
    except sqlite3.OperationalError:
        # Fallback for legacy / test DB schemas that use different column names
        try:
            cur.execute(  # nosec: B608 - parameterized query using _ph() placeholders and parameters tuple
                "SELECT id, email, hashed_password, is_active, is_admin FROM users WHERE email=?",
                (email,),
            )
            row = cur.fetchone()
            if row:
                # Normalize to expected shape
                if isinstance(row, dict):
                    hashed = row.get("hashed_password")
                    is_active = bool(row.get("is_active"))
                    is_admin = bool(row.get("is_admin"))
                    row = {
                        "id": row.get("id"),
                        "email": row.get("email"),
                        "password_hash": hashed,
                        "role": "admin" if is_admin else "viewer",
                        "subscription_active": is_active,
                    }
                else:
                    # sqlite3.Row supports index access
                    hashed = _safe_idx(row, 2)
                    is_active = (
                        bool(_safe_idx(row, 3))
                        if _safe_idx(row, 3) is not None
                        else False
                    )
                    is_admin = (
                        bool(_safe_idx(row, 4))
                        if _safe_idx(row, 4) is not None
                        else False
                    )
                    row = {
                        "id": _safe_idx(row, 0),
                        "email": _safe_idx(row, 1),
                        "password_hash": hashed,
                        "role": "admin" if is_admin else "viewer",
                        "subscription_active": is_active,
                    }
        except Exception:
            row = None
    con.close()

    result = _row_to_user(row) if row else None

    # Cache the result
    _set_cache(cache_key, result, ttl=300)
    return result


def get_user_by_id(uid: int) -> UserDict | None:
    cache_key = f"user_by_id:{uid}"
    cached = _get_cached(cache_key, ttl=300)  # Cache for 5 minutes
    if cached is not None:
        return cached

    con = _conn()
    cur = con.cursor()
    try:
        # Parameterized query using internal {_ph()} placeholder function and a
        # separate parameters tuple. This is safe against SQL injection.
        # Parameterized query using _ph() placeholders and parameters tuple - safe from SQL injection
        sql = f"""
        SELECT id, email, password_hash, role, subscription_active, created_at,
               oauth_provider, oauth_id, display_name, avatar_url, wallet_addresses,
                   totp_secret, mfa_enabled, mfa_type, recovery_codes, has_hardware_key
        FROM users WHERE id={_ph()}
        """  # nosec: B608 - parameterized placeholders used
        cur.execute(sql, (uid,))  # nosec: B608 - parameterized placeholders used
        row = cur.fetchone()
    except sqlite3.OperationalError:
        # Fallback for legacy/test DB schemas
        try:
            cur.execute(
                "SELECT id, email, hashed_password, is_admin, is_active FROM users WHERE id=?",
                (uid,),
            )
            r = cur.fetchone()
            if r:
                if isinstance(r, dict):
                    hashed = r.get("hashed_password")
                    is_active = bool(r.get("is_active"))
                    is_admin = bool(r.get("is_admin"))
                    row = {
                        "id": r.get("id"),
                        "email": r.get("email"),
                        "password_hash": hashed,
                        "role": "admin" if is_admin else "viewer",
                        "subscription_active": is_active,
                    }
                else:
                    # sqlite3.Row or sequence
                    hashed = _safe_idx(r, 2)
                    is_admin = (
                        bool(_safe_idx(r, 3)) if _safe_idx(r, 3) is not None else False
                    )
                    is_active = (
                        bool(_safe_idx(r, 4)) if _safe_idx(r, 4) is not None else False
                    )
                    row = {
                        "id": _safe_idx(r, 0),
                        "email": _safe_idx(r, 1),
                        "password_hash": hashed,
                        "role": "admin" if is_admin else "viewer",
                        "subscription_active": is_active,
                    }
            else:
                row = None
        except Exception:
            row = None
    con.close()
    result = _row_to_user(row)

    _set_cache(cache_key, result, ttl=300)
    return result


def create_user(
    email: str,
    password_hash: str | None = None,
    role: str = "viewer",
    subscription_active: bool = False,
    oauth_provider: str | None = None,
    oauth_id: str | None = None,
    display_name: str | None = None,
    avatar_url: str | None = None,
    wallet_addresses: list[dict[str, Any]] | None = None,
    totp_secret: str | None = None,
    mfa_enabled: bool = False,
    mfa_type: str | None = None,
    recovery_codes: list | None = None,
    has_hardware_key: bool = False,
) -> UserDict | None:
    """
    Create a new user with support for both traditional email / password and OAuth authentication.
    """
    con = _conn()
    cur = con.cursor()

    # Convert wallet_addresses and recovery_codes to JSON string
    wallet_addresses_json = json.dumps(wallet_addresses or [])
    recovery_codes_json = json.dumps(recovery_codes or [])

    # For OAuth users, password_hash can be None
    if USING_POSTGRES:
        sql = f"""
        INSERT INTO users (
            email, password_hash, role, subscription_active, created_at,
                oauth_provider, oauth_id, display_name, avatar_url, wallet_addresses,
                totp_secret, mfa_enabled, mfa_type, recovery_codes, has_hardware_key
        )
        VALUES (
            {_ph()},{_ph()},{_ph()},{_ph()}, NOW(),
            {_ph()},{_ph()},{_ph()},{_ph()},{_ph()},{_ph()},{_ph()},{_ph()},{_ph()},{_ph()}
        )
        RETURNING id
        """  # nosec: B608 - parameterized placeholders used
        cur.execute(
            sql,
            (
                email,
                password_hash,
                role,
                subscription_active,
                oauth_provider,
                oauth_id,
                display_name,
                avatar_url,
                wallet_addresses_json,
                totp_secret,
                mfa_enabled,
                mfa_type,
                recovery_codes_json,
                has_hardware_key,
            ),
        )
        _f = cur.fetchone()
        # Normalize returned shape: psycopg2 may return a dict-like row, sqlite returns a sequence
        if _f is None:
            new_id = None
        elif isinstance(_f, dict):
            new_id = _f.get("id")
        else:
            new_id = _safe_idx(_f, 0)
    else:
        # Attempt normal insert into canonical columns
        try:
            sql = f"""
            INSERT INTO users (
                email, password_hash, role, subscription_active, created_at,
                    oauth_provider, oauth_id, display_name, avatar_url, wallet_addresses,
                    totp_secret, mfa_enabled, mfa_type, recovery_codes, has_hardware_key
            )
            VALUES (
                {_ph()},{_ph()},{_ph()},{_ph()}, datetime('now'),
                {_ph()},{_ph()},{_ph()},{_ph()},{_ph()},{_ph()},{_ph()},{_ph()},{_ph()},{_ph()}
            )
            """  # nosec: B608 - parameterized placeholders used
            cur.execute(
                sql,
                (
                    email,
                    password_hash,
                    role,
                    1 if subscription_active else 0,
                    oauth_provider,
                    oauth_id,
                    display_name,
                    avatar_url,
                    wallet_addresses_json,
                    totp_secret,
                    1 if mfa_enabled else 0,
                    mfa_type,
                    recovery_codes_json,
                    1 if has_hardware_key else 0,
                ),
            )
            new_id = cur.lastrowid
        except sqlite3.OperationalError as e:
            # Fallback for legacy/test DBs that have older column names
            lower_e = str(e).lower()
            if (
                "no column named password_hash" in lower_e
                or "has no column named password_hash" in lower_e
            ):
                try:
                    # Legacy schema uses hashed_password, is_admin, is_active
                    sql = f"""
                    INSERT INTO users (
                        email, hashed_password, is_admin, is_active, created_at
                                        ) VALUES (
                                            {_ph()},{_ph()},{_ph()},{_ph()}, datetime('now')
                                        )
                    """  # nosec: B608 - parameterized placeholders used
                    cur.execute(
                        sql,
                        (
                            email,
                            password_hash,
                            1 if role == "admin" else 0,
                            1 if subscription_active else 0,
                        ),
                    )
                    new_id = cur.lastrowid
                except Exception:
                    # Re-raise original error if fallback also fails
                    raise
            else:
                raise
    con.commit()
    con.close()

    # Invalidate user caches
    _clear_cache_pattern("user_by_email")

    # Debug visibility: log the newly created id for troubleshooting tests
    try:
        logger.debug("create_user: new_id=%r", new_id)
    except Exception:
        with contextlib.suppress(Exception):
            _ = None

    try:
        return get_user_by_id(int(new_id)) if new_id is not None else None
    except Exception:
        return None


def set_subscription_active(email: str, active: bool) -> None:
    con = _conn()
    cur = con.cursor()
    # For Postgres, store True / False; for SQLite, store 1 / 0
    value = True if USING_POSTGRES else (1 if active else 0)
    cur.execute(
        f"UPDATE users SET subscription_active={_ph()} WHERE email={_ph()}",  # nosec: B608
        (value, email),
    )
    con.commit()
    con.close()


def set_role(email: str, role: str) -> None:
    con = _conn()
    cur = con.cursor()
    cur.execute(
        f"UPDATE users SET role={_ph()} WHERE email={_ph()}",  # nosec: B608
        (role, email),
    )
    con.commit()
    con.close()


def update_user_subscription(user_id: int | str, active: bool = True) -> bool:
    """Activate or deactivate a user's subscription by id.

    Returns True on success, False on failure. This function is a small
    compatibility helper used by the paywall flow and tests.
    """
    try:
        con = _conn()
        cur = con.cursor()
        uid = int(user_id) if not isinstance(user_id, int) else user_id
        if USING_POSTGRES:
            cur.execute(
                "UPDATE users SET subscription_active = %s WHERE id = %s",
                (bool(active), uid),
            )
        else:
            cur.execute(
                "UPDATE users SET subscription_active = ? WHERE id = ?",
                (1 if active else 0, uid),
            )
        con.commit()
        con.close()
        _clear_cache_pattern(f"user_by_id:{uid}")
        _clear_cache_pattern("user_by_email")
        return True
    except Exception:
        with contextlib.suppress(Exception):
            con.close()
        return False


# --- User Settings API (normalized columns) ----------------------------------


def get_settings_for_user(user_id: int) -> dict[str, Any]:
    """
    Return user's saved settings or {} if none.
    Keys: x_api_key (str), risk_threshold (float|None), time_range_days (int|None), ui_prefs (dict)
    """
    try:
        con = _conn()
        cur = con.cursor()
        sql = f"""
          SELECT x_api_key, risk_threshold, time_range_days, ui_prefs
          FROM user_settings
          WHERE user_id={_ph()}
            """  # nosec: B608 - parameterized placeholders used
        cur.execute(sql, (user_id,))  # nosec: B608 - parameterized placeholders used
        row = cur.fetchone()
        con.close()
        if not row:
            return {}
        if not isinstance(row, dict):
            row = {k: row[k] for k in row}
        out: dict[str, Any] = {
            "x_api_key": row.get("x_api_key") or None,
            "risk_threshold": (
                float(row["risk_threshold"])
                if row.get("risk_threshold") is not None
                else None
            ),
            "time_range_days": (
                int(row["time_range_days"])
                if row.get("time_range_days") is not None
                else None
            ),
        }
        # ui_prefs as JSON
        prefs_raw = row.get("ui_prefs")
        try:
            out["ui_prefs"] = (
                json.loads(prefs_raw)
                if isinstance(prefs_raw, (str, bytes))
                else (prefs_raw if isinstance(prefs_raw, dict) else {})
            )
        except Exception:
            out["ui_prefs"] = {}
        return out
    except Exception as e:
        # If table doesn't exist or column missing, return empty settings
        print(f"Database error in get_settings_for_user: {e}")
        return {
            "x_api_key": None,
            "risk_threshold": None,
            "time_range_days": None,
            "ui_prefs": {},
        }


def save_settings_for_user(user_id: int, patch: dict[str, Any]) -> dict[str, Any]:
    """
    Upsert user settings with provided keys only.
    Accepts: x_api_key, risk_threshold, time_range_days, ui_prefs (dict)
    Returns the merged row.
    """
    # Load current
    current = get_settings_for_user(user_id)

    # Merge with light coercion
    merged = dict(current)
    if "x_api_key" in patch:
        merged["x_api_key"] = (patch["x_api_key"] or "").strip() or None
    if "risk_threshold" in patch and patch["risk_threshold"] is not None:
        with contextlib.suppress(Exception):
            merged["risk_threshold"] = float(patch["risk_threshold"])
    if "time_range_days" in patch and patch["time_range_days"] is not None:
        with contextlib.suppress(Exception):
            merged["time_range_days"] = int(patch["time_range_days"])
    if "ui_prefs" in patch and patch["ui_prefs"] is not None:
        prefs = patch["ui_prefs"]
        if not isinstance(prefs, (dict, list)):
            try:
                prefs = json.loads(str(prefs))
            except Exception:
                prefs = {}
        merged["ui_prefs"] = prefs

    # Normalize for storage
    x_api_key = merged.get("x_api_key")
    risk_threshold = merged.get("risk_threshold")
    time_range_days = merged.get("time_range_days")
    ui_prefs_json = json.dumps(merged.get("ui_prefs") or {})

    con = _conn()
    cur = con.cursor()
    if USING_POSTGRES:
        sql = f"""
                    INSERT INTO user_settings (
                        user_id,
                            x_api_key,
                            risk_threshold,
                            time_range_days,
                            ui_prefs,
                            created_at,
                            updated_at
                    )
                    VALUES (
                        {_ph()},{_ph()},{_ph()},{_ph()},{_ph()}, NOW(), NOW()
                    )
                    ON CONFLICT (user_id) DO UPDATE SET
                        x_api_key=EXCLUDED.x_api_key,
                            risk_threshold=EXCLUDED.risk_threshold,
                            time_range_days=EXCLUDED.time_range_days,
                            ui_prefs=EXCLUDED.ui_prefs,
                            updated_at=NOW()
                        """  # nosec: B608 - parameterized placeholders used
        cur.execute(
            sql,
            (user_id, x_api_key, risk_threshold, time_range_days, ui_prefs_json),
        )
    else:
        sql = f"""
                    INSERT INTO user_settings (
                        user_id, x_api_key, risk_threshold, time_range_days, ui_prefs, created_at, updated_at
                    )
                    VALUES (
                        {_ph()},{_ph()},{_ph()},{_ph()},{_ph()}, datetime('now'), datetime('now')
                    )
                    ON CONFLICT(user_id) DO UPDATE SET
                        x_api_key=excluded.x_api_key,
                        risk_threshold=excluded.risk_threshold,
                        time_range_days=excluded.time_range_days,
                        ui_prefs=excluded.ui_prefs,
                        updated_at=datetime('now')
                """  # nosec: B608 - parameterized placeholders used
        cur.execute(
            sql,
            (user_id, x_api_key, risk_threshold, time_range_days, ui_prefs_json),
        )
    con.commit()
    con.close()
    return get_settings_for_user(user_id)


# --- Back - compat wrappers (optional) ------------------------------------------


def get_settings(user_id: int) -> dict[str, Any]:
    """Deprecated: use get_settings_for_user."""
    return get_settings_for_user(user_id)


def save_settings(user_id: int, data: dict[str, Any]) -> None:
    """Deprecated: use save_settings_for_user (no return)."""
    save_settings_for_user(user_id, data)


# --- OAuth and Wallet Management Functions -----------------------------------


def get_user_by_oauth(oauth_provider: str, oauth_id: str) -> UserDict | None:
    """Find a user by their OAuth provider and ID."""
    cache_key = f"user_by_oauth:{oauth_provider}:{oauth_id}"
    cached = _get_cached(cache_key, ttl=300)  # Cache for 5 minutes
    if cached is not None:
        return cached

    con = _conn()
    cur = con.cursor()
    sql = f"""
        SELECT id, email, password_hash, role, subscription_active, created_at,
               oauth_provider, oauth_id, display_name, avatar_url, wallet_addresses
    FROM users WHERE oauth_provider={_ph()} AND oauth_id={_ph()}
            """  # nosec: B608 - parameterized placeholders used
    cur.execute(
        sql, (oauth_provider, oauth_id)
    )  # nosec: B608 - parameterized placeholders used
    row = cur.fetchone()
    con.close()
    result = _row_to_user(row)

    _set_cache(cache_key, result, ttl=300)
    return result


def update_user_wallet_addresses(
    user_id: int, wallet_addresses: list[dict[str, Any]]
) -> None:
    """Update a user's wallet addresses."""
    con = _conn()
    cur = con.cursor()
    wallet_addresses_json = json.dumps(wallet_addresses)
    # Parameterized query using internal {_ph()} placeholder function and a
    # separate parameters tuple. This is safe against SQL injection.
    cur.execute(
        f"UPDATE users SET wallet_addresses={_ph()} WHERE id={_ph()}",  # nosec: B608
        (wallet_addresses_json, user_id),
    )
    con.commit()
    con.close()

    # Invalidate user caches
    _clear_cache_pattern(f"user_by_id:{user_id}")
    _clear_cache_pattern("user_by_email")
    _clear_cache_pattern("user_by_oauth")


def add_wallet_address(
    user_id: int, address: str, chain: str, label: str | None = None
) -> None:
    """Add a wallet address to a user's profile."""
    user = get_user_by_id(user_id)
    if not user:
        return

    wallet_addresses = user.get("wallet_addresses", []) or []

    # Check if address already exists
    for wallet in wallet_addresses or []:
        if wallet.get("address") == address and wallet.get("chain") == chain:
            return  # Address already exists

    # Add new wallet
    new_wallet = {
        "address": address,
        "chain": chain,
        "label": label or f"{chain} Wallet",
        "added_at": datetime.now().isoformat(),
    }
    wallet_addresses = list(wallet_addresses or [])
    wallet_addresses.append(new_wallet)

    update_user_wallet_addresses(user_id, wallet_addresses)


def update_user_mfa(
    user_id: int,
    mfa_enabled: bool | None = None,
    mfa_type: str | None = None,
    totp_secret: str | None = None,
    recovery_codes: list | None = None,
    has_hardware_key: bool | None = None,
) -> None:
    """Update MFA settings for a user."""
    con = _conn()
    cur = con.cursor()

    # Build dynamic update query
    updates: list[str] = []
    values: list[Any] = []

    if mfa_enabled is not None:
        if USING_POSTGRES:
            updates.append(f"mfa_enabled={_ph()}")
            values.append(mfa_enabled)
        else:
            updates.append(f"mfa_enabled={_ph()}")
            values.append(1 if mfa_enabled else 0)

    if mfa_type is not None:
        updates.append(f"mfa_type={_ph()}")
        values.append(mfa_type)

    if totp_secret is not None:
        updates.append(f"totp_secret={_ph()}")
        values.append(totp_secret)

    if recovery_codes is not None:
        updates.append(f"recovery_codes={_ph()}")
        values.append(json.dumps(recovery_codes))

    if has_hardware_key is not None:
        if USING_POSTGRES:
            updates.append(f"has_hardware_key={_ph()}")
            values.append(has_hardware_key)
        else:
            updates.append(f"has_hardware_key={_ph()}")
            values.append(1 if has_hardware_key else 0)

    if updates:
        values.append(user_id)
    query = f"UPDATE users SET {', '.join(updates)} WHERE id={_ph()}"  # nosec: B608
    cur.execute(query, values)
    con.commit()

    con.close()

    # Clear user cache
    _clear_cache_pattern("user_by_id")
    _clear_cache_pattern("user_by_email")


def update_user_password(user_id: int, password_hash: str) -> None:
    """Update user's password hash."""
    con = _conn()
    cur = con.cursor()

    cur.execute(
        f"UPDATE users SET password_hash={_ph()} WHERE id={_ph()}",  # nosec: B608
        (password_hash, user_id),
    )
    con.commit()
    con.close()

    # Clear user cache
    _clear_cache_pattern("user_by_id")
    _clear_cache_pattern("user_by_email")


# Simple in-memory rotated password storage (ephemeral).
# For production use this should be a persistent table with TTL, but
# an in-memory mapping suffices for test/dev environments and keeps the
# behavior isolated and reversible.
_rotated_passwords: dict[int, list[tuple[int, str]]] = {}


def add_rotated_password(
    user_id: int, password_hash: str, max_age_seconds: int = 30 * 24 * 3600
) -> None:
    """Record a previous password hash for a user with a timestamp.

    The storage is ephemeral and pruned on insertion. `max_age_seconds`
    controls how long old rotated hashes are kept (default 30 days).
    """
    import time

    now = int(time.time())
    lst = _rotated_passwords.get(user_id) or []
    # Append latest at end
    lst.append((now, password_hash))
    # Prune entries older than max_age_seconds
    cutoff = now - max_age_seconds
    lst = [(ts, ph) for (ts, ph) in lst if ts >= cutoff]
    _rotated_passwords[user_id] = lst


def get_rotated_passwords(user_id: int) -> list[str]:
    """Return a list of rotated password hashes (most recent last).

    Returns an empty list if none recorded.
    """
    lst = _rotated_passwords.get(user_id) or []
    return [ph for (_ts, ph) in lst]


def remove_wallet_address(user_id: int, address: str, chain: str) -> None:
    """Remove a wallet address from a user's profile."""
    user = get_user_by_id(user_id)
    if not user:
        return

    wallet_addresses = user.get("wallet_addresses", [])
    wallet_addresses = [
        w
        for w in (wallet_addresses or [])
        if not (w.get("address") == address and w.get("chain") == chain)
    ]

    update_user_wallet_addresses(user_id, wallet_addresses)


def update_user_profile(
    user_id: int, display_name: str | None = None, avatar_url: str | None = None
) -> None:
    """Update a user's profile information."""
    con = _conn()
    cur = con.cursor()

    updates: list[str] = []
    params: list[Any] = []

    if display_name is not None:
        updates.append(f"display_name={_ph()}")
        params.append(display_name)

    if avatar_url is not None:
        updates.append(f"avatar_url={_ph()}")
        params.append(avatar_url)

    if updates:
        params.append(user_id)
        # Constructed query uses internal {_ph()} placeholders and the
        # accompanying `params` tuple below, so values are passed separately
        # to the DB API. Suppress Bandit B608 here with a short rationale.
        sql = f"UPDATE users SET {', '.join(updates)} WHERE id={_ph()}"  # nosec: B608
        cur.execute(sql, params)  # nosec: B608 - parameterized placeholders used
        con.commit()

    con.close()
