import os
import sqlite3
import tempfile
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_low_amount_no_high_amount_tag_isolated_db():
    """Canonical path should not mirror HIGH_AMOUNT for low amounts (< 50000)."""
    # Isolated DB
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = Path(tmp.name)

    prev_db = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"

    # Init canonical schema and ensure compliance_tags exists (for lookup)
    from app import store

    store.init_db()

    conn = sqlite3.connect(db_path.as_posix())
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS compliance_tags (
                id INTEGER PRIMARY KEY,
                transaction_id INTEGER NOT NULL,
                tag_type TEXT NOT NULL,
                confidence REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
    finally:
        conn.close()

    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Register and login (JSON API)
        email = "nohigh@example.com"
        password = "Str0ng!Passw0rd"
        r = await client.post(
            "/auth/register", json={"email": email, "password": password}
        )
        assert r.status_code in (200, 201)
        r = await client.post(
            "/auth/login/api", json={"email": email, "password": password}
        )
        assert r.status_code == 200

        # Create a low-amount transaction via canonical path
        payload = {"amount": 49999.99, "currency": "USD", "status": "completed"}
        resp = await client.post("/transactions", json=payload)
        assert resp.status_code in (200, 201)
        tx_id = resp.json().get("id")
        assert isinstance(tx_id, int)

        # Fetch compliance tags: should not contain HIGH_AMOUNT
        tags_resp = await client.get(f"/transactions/{tx_id}/compliance-tags")
        assert tags_resp.status_code == 200
        tags = tags_resp.json()
        assert isinstance(tags, list)
        assert not any(t.get("tag_type") == "HIGH_AMOUNT" for t in tags)

    # Cleanup env
    if prev_db is not None:
        os.environ["DATABASE_URL"] = prev_db
    else:
        os.environ.pop("DATABASE_URL", None)
    try:
        db_path.unlink(missing_ok=True)
    except Exception:
        pass
