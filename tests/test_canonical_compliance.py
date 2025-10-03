import os
import sqlite3
import tempfile
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_high_amount_tag_canonical_isolated_db():
    """Force canonical txs path using an isolated temp DB and verify HIGH_AMOUNT tag.

    We create a dedicated sqlite DB for this test (no legacy 'transactions' table),
    initialize the canonical schema via store.init_db(), then exercise the flow:
    register -> login -> create high-value tx -> fetch compliance tags.
    """
    # Prepare isolated temp DB and environment
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = Path(tmp.name)

    prev_db = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"

    # Initialize canonical schema (txs + users) for the isolated DB
    from app import store

    store.init_db()

    # Ensure legacy compliance_tags table exists for mirrored tags lookup
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

    # Create an isolated client bound to the ASGI app
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1) Register with a strong password to satisfy policy
        r = await client.post(
            "/auth/register",
            json={"email": "canon@example.com", "password": "Str0ng!Passw0rd"},
        )
        assert r.status_code in (200, 201)

        # 2) Login via JSON API endpoint (avoid form-based /auth/login)
        r = await client.post(
            "/auth/login/api",
            json={"email": "canon@example.com", "password": "Str0ng!Passw0rd"},
        )
        if r.status_code != 200:
            # aid debugging in CI logs
            try:
                print("/auth/login response:", r.status_code, r.json())
            except Exception:
                print("/auth/login response:", r.status_code, r.text)
        assert r.status_code == 200
        data = r.json()
        assert data.get("ok") is True
        assert "access_token" in data

        # 3) Create a high-value transaction via canonical path
        payload = {"amount": 60000.0, "currency": "USD", "status": "completed"}
        resp = await client.post("/transactions", json=payload)
        assert resp.status_code in (200, 201)
        tx = resp.json()
        tx_id = tx.get("id")
        assert isinstance(tx_id, int)

        # 4) Fetch compliance tags from legacy table for created ID
        tags_resp = await client.get(f"/transactions/{tx_id}/compliance-tags")
        assert tags_resp.status_code == 200
        tags = tags_resp.json()
        assert isinstance(tags, list)
        assert any(t.get("tag_type") == "HIGH_AMOUNT" for t in tags)
        conf = max(
            (
                t.get("confidence", 0)
                for t in tags
                if t.get("tag_type") == "HIGH_AMOUNT"
            ),
            default=0,
        )
        assert conf >= 0.8

    # Cleanup and restore env
    if prev_db is not None:
        os.environ["DATABASE_URL"] = prev_db
    else:
        os.environ.pop("DATABASE_URL", None)
    try:
        db_path.unlink(missing_ok=True)
    except Exception:
        pass
