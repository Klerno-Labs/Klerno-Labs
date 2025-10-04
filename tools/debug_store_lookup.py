import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import cast

from app._typing_shims import ISyncConnection

# Ensure repo root on sys.path
ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
    db_path = tmp.name

conn = cast("ISyncConnection", sqlite3.connect(db_path))
conn.execute(
    """
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    is_admin BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""",
)
conn.execute(
    "INSERT INTO users (email, hashed_password, is_active, is_admin) VALUES (?, ?, ?, ?)",
    ("test@example.com", "$2b$12$test_hash", 1, 0),
)
conn.commit()
conn.close()

# To avoid selecting Postgres (psycopg present in the venv), leave DATABASE_URL empty
# and set DB_PATH so store._sqlite_conn will use our temporary DB file.
os.environ["DATABASE_URL"] = ""
os.environ["DB_PATH"] = db_path

from app import store

user = store.get_user_by_email("test@example.com")
print("user:", user)
print("user keys:", list(user.keys()) if user else None)

# cleanup
from contextlib import suppress

with suppress(Exception):
    Path(db_path).unlink()
