# ruff: noqa: E402
import contextlib
import os
import sqlite3
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

# Create temp DB and schema like tests
with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
    db_path = tmp.name

conn = sqlite3.connect(db_path)
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
    """
)
conn.commit()
conn.close()

os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

from app.main import app

client = TestClient(app)

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

# cleanup (best-effort)
with contextlib.suppress(Exception):
    Path(db_path).unlink()
