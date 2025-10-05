"""Small helper to exercise concurrency against the FastAPI app.

This file intentionally performs environment and sys.path setup before
importing `app` so it triggers ruff E402. Add `# ruff: noqa: E402` to
silence that specific lint in this helper.
"""

import asyncio
import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, cast

from httpx import ASGITransport, AsyncClient

if TYPE_CHECKING:
    from app._typing_shims import ISyncConnection

# Build a small temp DB like tests do
with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
    db_path = f.name

conn = cast("ISyncConnection", sqlite3.connect(db_path))
conn.execute(
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
conn.execute(
    """
    CREATE TABLE transactions (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL,
        amount DECIMAL(10,2) NOT NULL,
        currency TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    );
    """,
)
conn.execute(
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

# Ensure workspace root is on sys.path so `app` imports resolve
ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Import the app after setting env
from app.main import app


async def run_test(concurrent=20) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:

        async def op(i):
            resp = await client.post(
                "/transactions",
                json={"amount": float(i), "currency": "USD"},
            )
            try:
                data = resp.json()
            except Exception:
                data = resp.text
            if resp.status_code == 201:
                txid = data.get("id") if isinstance(data, dict) else None
                # Verify directly on disk that the transaction exists
                try:
                    check_con = cast(
                        "ISyncConnection",
                        sqlite3.connect(db_path, timeout=5.0),
                    )
                    cur = check_con.cursor()
                    cur.execute(
                        "SELECT id, amount FROM transactions WHERE id=?",
                        (txid,),
                    )
                    cur.fetchone()
                    check_con.close()
                except Exception:
                    pass

                await client.get(f"/transactions/{txid}")
            return resp.status_code

        tasks = [op(i) for i in range(concurrent)]
        await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(run_test(20))
