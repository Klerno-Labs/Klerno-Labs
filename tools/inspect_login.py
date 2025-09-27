# ruff: noqa: E402
import contextlib
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

# create a small temp sqlite DB with legacy schema
with tempfile.NamedTemporaryFile(
    prefix="klerno_test_", suffix=".db", delete=False
) as _tmp:
    db_path = _tmp.name

# ensure import path
from pathlib import Path as _Path

# Ensure project root on sys.path using pathlib for clarity
project_root = _Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# create DB and seed legacy-style columns
con = sqlite3.connect(db_path)
cur = con.cursor()
cur.execute(
    """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    email TEXT UNIQUE,
    hashed_password TEXT,
    is_active INTEGER DEFAULT 1,
    is_admin INTEGER DEFAULT 0
)
"""
)
cur.execute(
    "INSERT OR REPLACE INTO users (id, email, hashed_password, is_active, is_admin) VALUES (1, 'test@example.com', '$2b$12$test_hash', 1, 0)"
)
con.commit()
con.close()

# Force the app to use this sqlite DB by setting DATABASE_URL and DB_PATH
# Important: do this BEFORE importing the app so app.store picks the sqlite code path
os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
os.environ["DB_PATH"] = db_path

print("DEBUG: env DATABASE_URL before import:", os.environ.get("DATABASE_URL"))
print("DEBUG: env DB_PATH before import:", os.environ.get("DB_PATH"))

import importlib

# Import the app after setting env; if any modules were previously imported
# (e.g. in a long-running interpreter), attempt to reload key modules so
# they re-evaluate DATABASE_URL/DB_PATH at runtime.
from app.main import app

# Best-effort: reload store/security modules so they pick up the runtime env
try:
    import app.store as _store

    importlib.reload(_store)
except Exception:
    with contextlib.suppress(Exception):
        _ = None
try:
    import app.security_session as _ss

    importlib.reload(_ss)
except Exception:
    with contextlib.suppress(Exception):
        _ = None

# Seed a test user into the temporary DB using the app's hash function so
# verification is consistent with runtime. Import after setting DB env so the
# app/store resolves the same DB file.
try:
    from app.security_session import hash_pw

    pw = "testpassword"
    admin_pw = "adminpassword"
    pw_hash = hash_pw(pw)
    admin_hash = hash_pw(admin_pw)

    con = sqlite3.connect(db_path)
    cur = con.cursor()
    # Insert into legacy hashed_password column; store.get_user_by_email will
    # normalize this into password_hash for the auth path.
    cur.execute(
        "INSERT OR REPLACE INTO users (id, email, hashed_password, is_active, is_admin) VALUES (?, ?, ?, ?, ?)",
        (1, "test@example.com", pw_hash, 1, 0),
    )
    cur.execute(
        "INSERT OR REPLACE INTO users (id, email, hashed_password, is_active, is_admin) VALUES (?, ?, ?, ?, ?)",
        (2, "admin@example.com", admin_hash, 1, 1),
    )
    con.commit()
    con.close()
except Exception as e:
    print("Seed error:", type(e).__name__, str(e))

client = TestClient(app)

# Debug: ensure store can read the seeded user (print a short summary)
try:
    from app import store

    user_rec = store.get_user_by_email("test@example.com")
    print(
        "store.get_user_by_email ->",
        {k: user_rec.get(k) for k in ("id", "email", "role")} if user_rec else None,
    )
except Exception as e:
    print("store debug lookup failed:", type(e).__name__, str(e))

# Try posting form data as tests do
resp = client.post(
    "/auth/login",
    data={
        "username": "test@example.com",
        "password": "testpassword",
    },
)
print("status", resp.status_code)
try:
    print("json:", resp.json())
except Exception:
    print("text:", resp.text)

# Try JSON
resp2 = client.post(
    "/auth/login", json={"username": "test@example.com", "password": "testpassword"}
)
print("status json", resp2.status_code)
try:
    print("json2:", resp2.json())
except Exception:
    print("text2:", resp2.text)

# Try form-encoded with explicit email field and request JSON response (tests expect this)
resp3 = client.post(
    "/auth/login",
    data={"email": "test@example.com", "password": "testpassword"},
    headers={"accept": "application/json"},
)
print("status form-json-accept", resp3.status_code)
print("headers:", dict(resp3.headers))
try:
    print("json3:", resp3.json())
except Exception:
    print("text3:", resp3.text)

# Finally try a urlencoded POST with explicit content-type so the handler returns JSON
resp4 = client.post(
    "/auth/login",
    content="email=test@example.com&password=testpassword",
    headers={
        "content-type": "application/x-www-form-urlencoded",
        "accept": "application/json",
    },
)
print("status form-urlencoded json-accept", resp4.status_code)
try:
    print("json4:", resp4.json())
except Exception:
    print("text4:", resp4.text[:200])

# Direct API JSON call to /auth/login/api (programmatic API)
resp5 = client.post(
    "/auth/login/api",
    json={"email": "test@example.com", "password": "testpassword"},
)
print("status api-json", resp5.status_code)
try:
    print("json5:", resp5.json())
except Exception:
    print("text5:", resp5.text[:200])

# cleanup (best-effort)
with contextlib.suppress(Exception):
    Path(db_path).unlink()
