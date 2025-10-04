import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import cast

from fastapi.testclient import TestClient

from app._typing_shims import ISyncConnection

# Ensure workspace root is on sys.path (like tests/conftest.py)
ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Create a temp DB matching tests fixture
with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
    db_path = tmp.name

conn = cast("ISyncConnection", sqlite3.connect(db_path))
cur = conn.cursor()
cur.execute(
    """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        hashed_password TEXT NOT NULL,
        is_active BOOLEAN DEFAULT 1,
        is_admin BOOLEAN DEFAULT 0,
        subscription_status TEXT DEFAULT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
)
cur.execute(
    """
    CREATE TABLE transactions (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL,
        amount DECIMAL(10, 2) NOT NULL,
        currency TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    );
    """,
)
cur.execute(
    """
    CREATE TABLE compliance_tags (
        id INTEGER PRIMARY KEY,
        transaction_id INTEGER NOT NULL,
        tag_type TEXT NOT NULL,
        confidence REAL NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (transaction_id) REFERENCES transactions (id)
    );
    """,
)
conn.commit()
conn.close()

os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

from app.main import app

with TestClient(app) as client:
    resp = client.post("/transactions", json={"amount": 10.0, "currency": "USD"})
    print("POST status", resp.status_code)
    print("POST headers:", resp.headers)
    print("POST content bytes:", resp.content)
    print("POST text:", resp.text)
    if resp.status_code == 201:
        try:
            txid = resp.json().get("id")
        except Exception as e:
            print("Failed to parse JSON:", e)
            txid = None
        if txid:
            r2 = client.get(f"/transactions/{txid}")
            print("GET status", r2.status_code, r2.text)

print("DB file at", db_path)
