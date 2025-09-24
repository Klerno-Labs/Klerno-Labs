# ruff: noqa: E402
import asyncio
import os
import sqlite3

# prepare temp DB
import tempfile
from pathlib import Path

from httpx import ASGITransport, AsyncClient

with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
    db_path = tmp.name

conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute(
    """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        email TEXT
    );
    """
)
cur.execute(
    """
    CREATE TABLE transactions (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        currency TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
)
cur.execute(
    """
    CREATE TABLE compliance_tags (
        id INTEGER PRIMARY KEY,
        transaction_id INTEGER NOT NULL,
        tag_type TEXT NOT NULL,
        confidence REAL NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
)
conn.commit()
conn.close()

os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

import sys

ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.main import app


async def run_batch(n=50):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:

        async def op(i):
            resp = await client.post(
                "/transactions", json={"amount": float(i), "currency": "USD"}
            )
            return resp.status_code, resp.text

        tasks = [op(i) for i in range(n)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, r in enumerate(results):
            print(i, type(r), r if isinstance(r, tuple) else repr(r))


asyncio.run(run_batch(50))
print("DB file", db_path)
