"""Seed the local SQLite DB at ./data/klerno.db with developer/admin users.

This uses the sentinel bcrypt hashes the app accepts in tests so no native
bcrypt binding is required. Run this from the project root with the venv active.
"""

import sqlite3
from pathlib import Path

DB = Path("data") / "klerno.db"
DB.parent.mkdir(parents=True, exist_ok=True)
con = sqlite3.connect(DB)
cur = con.cursor()

# Ensure a users table exists; if it doesn't, create a minimal canonical table.
cur.execute(
    """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    subscription_active INTEGER DEFAULT 0,
    is_admin INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""",
)

# Inspect existing columns and add canonical columns if missing. This avoids
# "no column named ..." sqlite errors on older or migrated DBs.
cur.execute("PRAGMA table_info(users);")
existing_cols = {r[1] for r in cur.fetchall()}


def add_col(name: str, col_def: str) -> None:
    if name not in existing_cols:
        try:
            cur.execute(f"ALTER TABLE users ADD COLUMN {col_def}")
            existing_cols.add(name)
        except Exception:
            # Best-effort: ignore failures to add (e.g., on locked DB)
            pass


# Ensure canonical columns exist
add_col("password_hash", "password_hash TEXT")
add_col("subscription_active", "subscription_active INTEGER DEFAULT 0")
add_col("is_admin", "is_admin INTEGER DEFAULT 0")

# Finally insert dev/admin users using canonical column names. We use
# INSERT OR IGNORE so repeated runs are safe.
try:
    cur.execute(
        "INSERT OR IGNORE INTO users (email, password_hash, subscription_active, is_admin) VALUES (?, ?, ?, ?)",
        ("dev@example.com", "$2b$12$test_hash", 1, 0),
    )
    cur.execute(
        "INSERT OR IGNORE INTO users (email, password_hash, subscription_active, is_admin) VALUES (?, ?, ?, ?)",
        ("admin@example.com", "$2b$12$admin_hash", 1, 1),
    )
except Exception:
    # If insertion using canonical columns fails for any reason, attempt
    # a fallback inserting into legacy column names.
    try:
        cur.execute(
            "INSERT OR IGNORE INTO users (email, hashed_password, is_active, is_admin) VALUES (?, ?, ?, ?)",
            ("dev@example.com", "$2b$12$test_hash", 1, 0),
        )
        cur.execute(
            "INSERT OR IGNORE INTO users (email, hashed_password, is_active, is_admin) VALUES (?, ?, ?, ?)",
            ("admin@example.com", "$2b$12$admin_hash", 1, 1),
        )
    except Exception:
        # Give up silently; user can inspect DB manually
        pass

con.commit()
con.close()
