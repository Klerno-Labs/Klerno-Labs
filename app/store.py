"""Data store utilities with SQLite / Postgres backends and lightweight caching."""
import json
import os
import sqlite3
import time
from datetime import datetime
from typing import List, Dict, Any, Iterable, Optional

# Simple in - memory cache for frequently accessed data
_cache={}
_cache_expiry={}
CACHE_TTL=300  # 5 minutes default TTL


def _get_cache_key(*args) -> str:
    """Generate cache key from arguments."""
    return "|".join(str(arg) for arg in args)


def _get_cached(key: str, ttl: int = CACHE_TTL):
    """Get cached value if not expired."""
    if key in _cache:
        if time.time() < _cache_expiry.get(key, 0):
            return _cache[key]
        else:
            # Expired, remove from cache
            _cache.pop(key, None)
            _cache_expiry.pop(key, None)
    return None


def _set_cache(key: str, value: Any, ttl: int = CACHE_TTL):
    """Set cached value with expiry."""
    _cache[key] = value
    _cache_expiry[key] = time.time() + ttl


def _clear_cache_pattern(pattern: str):
    """Clear cache entries matching pattern."""
    keys_to_remove=[k for k in _cache.keys() if pattern in k]
    for key in keys_to_remove:
        _cache.pop(key, None)
        _cache_expiry.pop(key, None)

# --- Config & detection -------------------------------------------------------

DATABASE_URL=os.getenv("DATABASE_URL") or ""

# Persistent SQLite path (fallback if not using Postgres)
BASE_DIR=os.path.dirname(__file__)
DB_PATH=os.getenv("DB_PATH", os.path.join(BASE_DIR, "..", "data", "klerno.db"))

# psycopg2 might not be installed locally; handle gracefully
try:
    import psycopg2  # type: ignore[import - not - found]
    from psycopg2.extras import RealDictCursor  # type: ignore[import - not - found]
    PSYCOPG2_AVAILABLE=True
except Exception:
    PSYCOPG2_AVAILABLE=False

USING_POSTGRES=bool(DATABASE_URL) and PSYCOPG2_AVAILABLE


# --- Connection factories -----------------------------------------------------


def _sqlite_conn() -> sqlite3.Connection:
    # honor DB_PATH and ensure directory exists
    data_dir=os.path.dirname(os.path.abspath(DB_PATH))
    os.makedirs(data_dir, exist_ok=True)
    con=sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory=sqlite3.Row  # return dict - like rows to unify handling
    return con


def _postgres_conn():
    # RealDictCursor returns dict rows (keyed by column name)
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)  # type: ignore[name - defined]


def _conn():
    """
    Return a DB connection:
    - Postgres if DATABASE_URL & psycopg2 are available
    - else SQLite
    """
    return _postgres_conn() if USING_POSTGRES else _sqlite_conn()


def _ph() -> str:
    """Return the correct SQL placeholder for the active backend."""
    return "%s" if USING_POSTGRES else "?"


# --- Schema management --------------------------------------------------------


def init_db() -> None:
    """
    Create tables if they do not exist:
      - txs           : transactions store
      - users         : auth / accounts
      - user_settings : per - user persisted settings (x_api_key, thresholds, etc.)
    Also adds helpful indexes.
    """
    con=_conn()
    cur=con.cursor()

    # ---- TXS TABLE ----
    if USING_POSTGRES:
        cur.execute("""
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
        );""")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_txs_from_addr ON txs (from_addr);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_txs_to_addr   ON txs (to_addr);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_txs_timestamp ON txs (timestamp);")
        # Additional indexes for admin analytics performance
        cur.execute("CREATE INDEX IF NOT EXISTS idx_txs_risk_score ON txs (risk_score);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_txs_category ON txs (category);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_txs_amount ON txs (amount);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_txs_timestamp_desc ON txs (timestamp DESC);")
    else:
        cur.execute("""
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
        );""")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_txs_from_addr ON txs (from_addr);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_txs_to_addr   ON txs (to_addr);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_txs_timestamp ON txs (timestamp);")
        # Additional indexes for admin analytics performance
        cur.execute("CREATE INDEX IF NOT EXISTS idx_txs_risk_score ON txs (risk_score);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_txs_category ON txs (category);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_txs_amount ON txs (amount);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_txs_timestamp_desc ON txs (timestamp DESC);")

    # ---- USERS TABLE ----
    if USING_POSTGRES:
        # users table: role can be 'admin' | 'analyst' | 'viewer'
        # OAuth provider data: 'google' | 'microsoft' | null (for email / password)
        # wallet_addresses stores a JSON array of wallet objects
        cur.execute("""
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
        );""")
        # Indexes for user queries
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users (role);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_created_at ON users (created_at);")
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_users_oauth_provider ON users (oauth_provider);"
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_oauth_id ON users (oauth_id);")
    else:
        # users table (SQLite): subscription_active uses 0 / 1
        # See notes above for role, OAuth provider fields, and wallet_addresses JSON
        cur.execute("""
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
        );""")
        # Basic indexes for user queries
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users (role);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_created_at ON users (created_at);")

    # Add columns to existing users table if they don't exist (migration)
    try:
        if USING_POSTGRES:
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS oauth_provider TEXT;")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS oauth_id TEXT;")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS display_name TEXT;")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url TEXT;")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS wallet_addresses TEXT DEFAULT '[]';")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_secret TEXT;")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE;")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_type TEXT;")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS recovery_codes TEXT DEFAULT '[]';")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS has_hardware_key BOOLEAN NOT NULL DEFAULT FALSE;")
        else:
            # SQLite doesn't support IF NOT EXISTS for ALTER TABLE, so we use a try / except
            for coldef in [
                ("totp_secret TEXT",),
                    ("mfa_enabled INTEGER NOT NULL DEFAULT 0",),
                    ("mfa_type TEXT",),
                    ("recovery_codes TEXT DEFAULT '[]'",),
                    ("has_hardware_key INTEGER NOT NULL DEFAULT 0",)
            ]:
                try:
                    cur.execute(f"ALTER TABLE users ADD COLUMN {coldef[0]};")
                except sqlite3.OperationalError:
                    pass
    except Exception as e:
        print(f"Migration warning: {e}")

    # Create indexes for new OAuth columns (after migration)
    try:
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_users_oauth_provider ON users (oauth_provider);"
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_oauth_id ON users (oauth_id);")
    except sqlite3.OperationalError:
        pass  # Columns might not exist yet

    # ---- USER_SETTINGS TABLE (normalized columns) ----
    if USING_POSTGRES:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                x_api_key TEXT,
                risk_threshold DOUBLE PRECISION,
                time_range_days INTEGER,
                ui_prefs JSONB,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );""")
    else:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
                x_api_key TEXT,
                risk_threshold REAL,
                time_range_days INTEGER,
                ui_prefs TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );""")

    con.commit()
    con.close()


# --- Row helpers --------------------------------------------------------------


def _rows_to_dicts(rows: Iterable) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for r in rows:
        # r can be psycopg2 RealDictRow (dict) or sqlite3.Row (mapping - like)
        if isinstance(r, dict):
            d=dict(r)
        else:
            d={k: r[k] for k in r.keys()}

        # normalize risk_flags to a list
        raw=d.get("risk_flags")
        try:
            d["risk_flags"] = json.loads(raw) if isinstance(raw, (str, bytes)) else (raw or [])
        except Exception:
            d["risk_flags"] = []

        out.append(d)
    return out


def _row_to_user(row) -> Optional[Dict[str, Any]]:
    if not row:
        return None
    if isinstance(row, dict):
        d=dict(row)
    else:
        d={k: row[k] for k in row.keys()}
    d["subscription_active"] = bool(d.get("subscription_active"))

    # Parse wallet addresses from JSON
    wallet_addresses_str=d.get("wallet_addresses", "[]")
    try:
        wallet_addresses=json.loads(wallet_addresses_str) if wallet_addresses_str else []
    except (json.JSONDecodeError, TypeError):
        wallet_addresses=[]

    # MFA fields
    recovery_codes_str=d.get("recovery_codes", "[]")
    try:
        recovery_codes=json.loads(recovery_codes_str) if recovery_codes_str else []
    except (json.JSONDecodeError, TypeError):
        recovery_codes=[]

    return {
        "id": d.get("id"),
            "email": d.get("email"),
            "password_hash": d.get("password_hash"),
            "role": d.get("role") or "viewer",
            "subscription_active": d.get("subscription_active"),
            "created_at": d.get("created_at"),
            "oauth_provider": d.get("oauth_provider"),
            "oauth_id": d.get("oauth_id"),
            "display_name": d.get("display_name"),
            "avatar_url": d.get("avatar_url"),
            "wallet_addresses": wallet_addresses,
            "totp_secret": d.get("totp_secret"),
            "mfa_enabled": bool(d.get("mfa_enabled", False)),
            "mfa_type": d.get("mfa_type"),
            "recovery_codes": recovery_codes,
            "has_hardware_key": bool(d.get("has_hardware_key", False)),
            }


# --- Transactions API ---------------------------------------------------------


def save_tagged(t: Dict[str, Any]) -> None:
    con=_conn()
    cur=con.cursor()
    p=_ph()
    cur.execute(f"""
      INSERT INTO txs (
        tx_id, timestamp, chain, from_addr, to_addr, amount, symbol, direction,
            memo, fee, category, risk_score, risk_flags, notes
      )
      VALUES ({p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p})
    """, (
        t["tx_id"], str(t["timestamp"]), t["chain"], t["from_addr"], t["to_addr"],
            float(t["amount"]), t["symbol"], t["direction"], t.get("memo"),
            float(t.get("fee") or 0.0), t.get("category", "unknown"),
            float(t.get("risk_score") or 0.0), json.dumps(t.get("risk_flags", [])),
            t.get("notes"),
            ))
    con.commit()
    con.close()

    # Invalidate transaction - related caches
    _clear_cache_pattern("list_all")
    _clear_cache_pattern("list_by_wallet")
    _clear_cache_pattern("list_alerts")


def list_by_wallet(wallet: str, limit: int = 100) -> List[Dict[str, Any]]:
    con=_conn()
    cur=con.cursor()
    p=_ph()
    cur.execute(f"""
      SELECT
        tx_id, timestamp, chain, from_addr, to_addr, amount, symbol, direction,
            memo, fee, category, risk_score, risk_flags, notes
      FROM txs
      WHERE from_addr={p} OR to_addr={p}
      ORDER BY id DESC
      LIMIT {p}
    """, (wallet, wallet, limit))
    rows=cur.fetchall()
    con.close()
    return _rows_to_dicts(rows)


def list_alerts(threshold: float = 0.75, limit: int = 100) -> List[Dict[str, Any]]:
    con=_conn()
    cur=con.cursor()
    p=_ph()
    cur.execute(f"""
      SELECT
        tx_id, timestamp, chain, from_addr, to_addr, amount, symbol, direction,
            memo, fee, category, risk_score, risk_flags, notes
      FROM txs
      WHERE risk_score >= {p}
      ORDER BY id DESC
      LIMIT {p}
    """, (threshold, limit))
    rows=cur.fetchall()
    con.close()
    return _rows_to_dicts(rows)


def list_all(limit: int = 1000) -> List[Dict[str, Any]]:
    # Check cache first
    cache_key=_get_cache_key("list_all", limit)
    cached_result=_get_cached(cache_key, ttl=60)  # Cache for 1 minute
    if cached_result is not None:
        return cached_result

    con=_conn()
    cur=con.cursor()
    p=_ph()
    cur.execute(f"""
      SELECT
        tx_id, timestamp, chain, from_addr, to_addr, amount, symbol, direction,
            memo, fee, category, risk_score, risk_flags, notes
      FROM txs
      ORDER BY id DESC
      LIMIT {p}
    """, (limit,))
    rows=cur.fetchall()
    con.close()
    result=_rows_to_dicts(rows)

    # Cache the result
    _set_cache(cache_key, result, ttl=60)
    return result


# --- Users API ----------------------------------------------------------------


def users_count() -> int:
    con=_conn()
    cur=con.cursor()
    cur.execute("SELECT COUNT(*) AS n FROM users")
    row=cur.fetchone()
    con.close()
    if isinstance(row, dict):
        return int(row.get("n", 0))
    return int(row[0]) if row else 0


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    # Check cache first
    cache_key=_get_cache_key("user_by_email", email.lower())
    cached_result=_get_cached(cache_key, ttl=300)  # Cache for 5 minutes
    if cached_result is not None:
        return cached_result

    con=_conn()
    cur=con.cursor()
    p=_ph()
    cur.execute(f"""
        SELECT id, email, password_hash, role, subscription_active, created_at,
               oauth_provider, oauth_id, display_name, avatar_url, wallet_addresses,
                   totp_secret, mfa_enabled, mfa_type, recovery_codes, has_hardware_key
        FROM users WHERE email={p}
    """, (email,))
    row=cur.fetchone()
    con.close()

    result=_row_to_user(row) if row else None

    # Cache the result
    _set_cache(cache_key, result, ttl=300)
    return result


def get_user_by_id(uid: int) -> Optional[Dict[str, Any]]:
    cache_key=f"user_by_id:{uid}"
    cached=_get_cached(cache_key, ttl=300)  # Cache for 5 minutes
    if cached is not None:
        return cached

    con=_conn()
    cur=con.cursor()
    p=_ph()
    cur.execute(f"""
        SELECT id, email, password_hash, role, subscription_active, created_at,
               oauth_provider, oauth_id, display_name, avatar_url, wallet_addresses,
                   totp_secret, mfa_enabled, mfa_type, recovery_codes, has_hardware_key
        FROM users WHERE id={p}
    """, (uid,))
    row=cur.fetchone()
    con.close()
    result=_row_to_user(row)

    _set_cache(cache_key, result, ttl=300)
    return result


def create_user(
    email: str,
        password_hash: str | None=None,
        role: str="viewer",
        subscription_active: bool=False,
        oauth_provider: str | None=None,
        oauth_id: str | None=None,
        display_name: str | None=None,
        avatar_url: str | None=None,
        wallet_addresses: List[Dict[str, Any]] | None=None,
        totp_secret: str | None=None,
        mfa_enabled: bool=False,
        mfa_type: str | None=None,
        recovery_codes: list | None=None,
        has_hardware_key: bool=False,
        ) -> Dict[str, Any]:
    """
    Create a new user with support for both traditional email / password and OAuth authentication.
    """
    con=_conn()
    cur=con.cursor()
    p=_ph()

    # Convert wallet_addresses and recovery_codes to JSON string
    wallet_addresses_json=json.dumps(wallet_addresses or [])
    recovery_codes_json=json.dumps(recovery_codes or [])

    # For OAuth users, password_hash can be None
    if USING_POSTGRES:
        cur.execute(
            f"""
            INSERT INTO users (
                email, password_hash, role, subscription_active, created_at,
                    oauth_provider, oauth_id, display_name, avatar_url, wallet_addresses,
                    totp_secret, mfa_enabled, mfa_type, recovery_codes, has_hardware_key
            )
            VALUES ({p},{p},{p},{p}, NOW(), {p},{p},{p},{p},{p},{p},{p},{p},{p},{p})
            RETURNING id
            """,
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
        new_id=cur.fetchone()["id"]
    else:
        cur.execute(
            f"""
            INSERT INTO users (
                email, password_hash, role, subscription_active, created_at,
                    oauth_provider, oauth_id, display_name, avatar_url, wallet_addresses,
                    totp_secret, mfa_enabled, mfa_type, recovery_codes, has_hardware_key
            )
            VALUES ({p},{p},{p},{p}, datetime('now'), {p},{p},{p},{p},{p},{p},{p},{p},{p},{p})
            """,
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
        new_id=cur.lastrowid
    con.commit()
    con.close()

    # Invalidate user caches
    _clear_cache_pattern("user_by_email")

    return get_user_by_id(int(new_id))


def set_subscription_active(email: str, active: bool) -> None:
    con=_conn()
    cur=con.cursor()
    p=_ph()
    # For Postgres, store True / False; for SQLite, store 1 / 0
    value=True if USING_POSTGRES else (1 if active else 0)
    cur.execute(f"UPDATE users SET subscription_active={p} WHERE email={p}", (value, email))
    con.commit()
    con.close()


def set_role(email: str, role: str) -> None:
    con=_conn()
    cur=con.cursor()
    p=_ph()
    cur.execute(f"UPDATE users SET role={p} WHERE email={p}", (role, email))
    con.commit()
    con.close()


# --- User Settings API (normalized columns) ----------------------------------


def get_settings_for_user(user_id: int) -> Dict[str, Any]:
    """
    Return user's saved settings or {} if none.
    Keys: x_api_key (str), risk_threshold (float|None), time_range_days (int|None), ui_prefs (dict)
    """
    try:
        con=_conn()
        cur=con.cursor()
        p=_ph()
        cur.execute(
            f"""
          SELECT x_api_key, risk_threshold, time_range_days, ui_prefs
          FROM user_settings
          WHERE user_id={p}
        """,
            (user_id,),
                )
        row=cur.fetchone()
        con.close()
        if not row:
            return {}
        if not isinstance(row, dict):
            row={k: row[k] for k in row.keys()}
        out: Dict[str, Any] = {
            "x_api_key": row.get("x_api_key") or None,
                "risk_threshold": (
                float(row["risk_threshold"]) if row.get("risk_threshold") is not None else None
            ),
                "time_range_days": (
                int(row["time_range_days"]) if row.get("time_range_days") is not None else None
            ),
                }
        # ui_prefs as JSON
        prefs_raw=row.get("ui_prefs")
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


def save_settings_for_user(user_id: int, patch: Dict[str, Any]) -> Dict[str, Any]:
    """
    Upsert user settings with provided keys only.
    Accepts: x_api_key, risk_threshold, time_range_days, ui_prefs (dict)
    Returns the merged row.
    """
    # Load current
    current=get_settings_for_user(user_id)

    # Merge with light coercion
    merged=dict(current)
    if "x_api_key" in patch:
        merged["x_api_key"] = (patch["x_api_key"] or "").strip() or None
    if "risk_threshold" in patch and patch["risk_threshold"] is not None:
        try:
            merged["risk_threshold"] = float(patch["risk_threshold"])
        except Exception:
            pass
    if "time_range_days" in patch and patch["time_range_days"] is not None:
        try:
            merged["time_range_days"] = int(patch["time_range_days"])
        except Exception:
            pass
    if "ui_prefs" in patch and patch["ui_prefs"] is not None:
        prefs=patch["ui_prefs"]
        if not isinstance(prefs, (dict, list)):
            try:
                prefs=json.loads(str(prefs))
            except Exception:
                prefs={}
        merged["ui_prefs"] = prefs

    # Normalize for storage
    x_api_key=merged.get("x_api_key")
    risk_threshold=merged.get("risk_threshold")
    time_range_days=merged.get("time_range_days")
    ui_prefs_json=json.dumps(merged.get("ui_prefs") or {})

    con=_conn()
    cur=con.cursor()
    p=_ph()
    if USING_POSTGRES:
                cur.execute(
                        f"""
                    INSERT INTO user_settings (
                        user_id,
                            x_api_key,
                            risk_threshold,
                            time_range_days,
                            ui_prefs,
                            created_at,
                            updated_at
                    )
                    VALUES ({p},{p},{p},{p},{p}, NOW(), NOW())
                    ON CONFLICT (user_id) DO UPDATE SET
                        x_api_key=EXCLUDED.x_api_key,
                            risk_threshold=EXCLUDED.risk_threshold,
                            time_range_days=EXCLUDED.time_range_days,
                            ui_prefs=EXCLUDED.ui_prefs,
                            updated_at=NOW()
                """,
                        (user_id, x_api_key, risk_threshold, time_range_days, ui_prefs_json),
                            )
    else:
        cur.execute(
            f"""
          INSERT INTO user_settings (
            user_id, x_api_key, risk_threshold, time_range_days, ui_prefs, created_at, updated_at
          )
          VALUES ({p},{p},{p},{p},{p}, datetime('now'), datetime('now'))
          ON CONFLICT(user_id) DO UPDATE SET
            x_api_key=excluded.x_api_key,
                risk_threshold=excluded.risk_threshold,
                time_range_days=excluded.time_range_days,
                ui_prefs=excluded.ui_prefs,
                updated_at=datetime('now')
        """,
            (user_id, x_api_key, risk_threshold, time_range_days, ui_prefs_json),
                )
    con.commit()
    con.close()
    return get_settings_for_user(user_id)


# --- Back - compat wrappers (optional) ------------------------------------------


def get_settings(user_id: int) -> Dict[str, Any]:
    """Deprecated: use get_settings_for_user."""
    return get_settings_for_user(user_id)


def save_settings(user_id: int, data: Dict[str, Any]) -> None:
    """Deprecated: use save_settings_for_user (no return)."""
    save_settings_for_user(user_id, data)


# --- OAuth and Wallet Management Functions -----------------------------------


def get_user_by_oauth(oauth_provider: str, oauth_id: str) -> Optional[Dict[str, Any]]:
    """Find a user by their OAuth provider and ID."""
    cache_key=f"user_by_oauth:{oauth_provider}:{oauth_id}"
    cached=_get_cached(cache_key, ttl=300)  # Cache for 5 minutes
    if cached is not None:
        return cached

    con=_conn()
    cur=con.cursor()
    p=_ph()
    cur.execute(f"""
        SELECT id, email, password_hash, role, subscription_active, created_at,
               oauth_provider, oauth_id, display_name, avatar_url, wallet_addresses
        FROM users WHERE oauth_provider={p} AND oauth_id={p}
    """, (oauth_provider, oauth_id))
    row=cur.fetchone()
    con.close()
    result=_row_to_user(row)

    _set_cache(cache_key, result, ttl=300)
    return result


def update_user_wallet_addresses(user_id: int, wallet_addresses: List[Dict[str, Any]]) -> None:
    """Update a user's wallet addresses."""
    con=_conn()
    cur=con.cursor()
    p=_ph()
    wallet_addresses_json=json.dumps(wallet_addresses)
    cur.execute(
        f"UPDATE users SET wallet_addresses={p} WHERE id={p}",
            (wallet_addresses_json, user_id),
            )
    con.commit()
    con.close()

    # Invalidate user caches
    _clear_cache_pattern(f"user_by_id:{user_id}")
    _clear_cache_pattern("user_by_email")
    _clear_cache_pattern("user_by_oauth")


def add_wallet_address(user_id: int, address: str, chain: str, label: str = None) -> None:
    """Add a wallet address to a user's profile."""
    user=get_user_by_id(user_id)
    if not user:
        return

    wallet_addresses=user.get("wallet_addresses", [])

    # Check if address already exists
    for wallet in wallet_addresses:
        if wallet.get("address") == address and wallet.get("chain") == chain:
            return  # Address already exists

    # Add new wallet
    new_wallet={
        "address": address,
            "chain": chain,
            "label": label or f"{chain} Wallet",
            "added_at": datetime.now().isoformat()
    }
    wallet_addresses.append(new_wallet)

    update_user_wallet_addresses(user_id, wallet_addresses)


def update_user_mfa(user_id: int, mfa_enabled: bool = None, mfa_type: str = None, totp_secret: str = None, recovery_codes: list = None, has_hardware_key: bool = None) -> None:
    """Update MFA settings for a user."""
    con=_conn()
    cur=con.cursor()
    p=_ph()

    # Build dynamic update query
    updates=[]
    values=[]

    if mfa_enabled is not None:
        if USING_POSTGRES:
            updates.append(f"mfa_enabled={p}")
            values.append(mfa_enabled)
        else:
            updates.append(f"mfa_enabled={p}")
            values.append(1 if mfa_enabled else 0)

    if mfa_type is not None:
        updates.append(f"mfa_type={p}")
        values.append(mfa_type)

    if totp_secret is not None:
        updates.append(f"totp_secret={p}")
        values.append(totp_secret)

    if recovery_codes is not None:
        updates.append(f"recovery_codes={p}")
        values.append(json.dumps(recovery_codes))

    if has_hardware_key is not None:
        if USING_POSTGRES:
            updates.append(f"has_hardware_key={p}")
            values.append(has_hardware_key)
        else:
            updates.append(f"has_hardware_key={p}")
            values.append(1 if has_hardware_key else 0)

    if updates:
        values.append(user_id)
        query=f"UPDATE users SET {', '.join(updates)} WHERE id={p}"
        cur.execute(query, values)
        con.commit()

    con.close()

    # Clear user cache
    _clear_cache_pattern("user_by_id")
    _clear_cache_pattern("user_by_email")


def update_user_password(user_id: int, password_hash: str) -> None:
    """Update user's password hash."""
    con=_conn()
    cur=con.cursor()
    p=_ph()

    cur.execute(f"UPDATE users SET password_hash={p} WHERE id={p}", (password_hash, user_id))
    con.commit()
    con.close()

    # Clear user cache
    _clear_cache_pattern("user_by_id")
    _clear_cache_pattern("user_by_email")


def remove_wallet_address(user_id: int, address: str, chain: str) -> None:
    """Remove a wallet address from a user's profile."""
    user=get_user_by_id(user_id)
    if not user:
        return

    wallet_addresses=user.get("wallet_addresses", [])
    wallet_addresses=[
        w
        for w in wallet_addresses
        if not (w.get("address") == address and w.get("chain") == chain)
    ]

    update_user_wallet_addresses(user_id, wallet_addresses)


def update_user_profile(user_id: int, display_name: str = None, avatar_url: str = None) -> None:
    """Update a user's profile information."""
    con=_conn()
    cur=con.cursor()
    p=_ph()

    updates=[]
    params=[]

    if display_name is not None:
        updates.append(f"display_name={p}")
        params.append(display_name)

    if avatar_url is not None:
        updates.append(f"avatar_url={p}")
        params.append(avatar_url)

    if updates:
        params.append(user_id)
        sql=f"UPDATE users SET {', '.join(updates)} WHERE id={p}"
        cur.execute(sql, params)
        con.commit()

    con.close()
