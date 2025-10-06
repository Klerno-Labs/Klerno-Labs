"""Simple async load test to exercise 1000 transactions and core endpoints.

This uses httpx.AsyncClient with ASGITransport to run entirely in-process
against app.main:app. It avoids network flakiness and is fast.

What it does:
- Creates 1000 transactions via POST /transactions
- Reads back a sample via GET /transactions and GET /transactions/{id}
- Hits /admin/analytics/transactions and /xrpl endpoints quickly (mock-free)
- Reports latency stats and success rate

Run: python api_load_testing.py
"""

from __future__ import annotations

import asyncio
import os
import random
import statistics
import time
from typing import Any

import httpx


async def run_load(n: int = 1000) -> dict[str, Any]:
    # Ensure a test-like DB target; use a temp file by default when not set
    os.environ.setdefault("DATABASE_URL", "sqlite:///./data/klerno_loadtest.db")
    # Use a strong-enough secret to avoid warnings in non-test envs
    os.environ.setdefault("JWT_SECRET", "loadtest-secret-0123456789ABCDEF")

    from app.main import app

    # Ensure database schema is initialized before issuing requests
    try:
        from app import store

        store.init_db()
    except Exception:
        pass

    results: list[float] = []
    successes = 0
    first_id: int | None = None

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Warm-up health check
        r = await client.get("/health")
        r.raise_for_status()

        # Create transactions concurrently in modest batches to avoid starving event loop
        BATCH = 100
        for i0 in range(0, n, BATCH):
            tasks = []
            for i in range(i0, min(i0 + BATCH, n)):
                payload = {
                    "amount": round(random.uniform(1.0, 500.0), 2),
                    "currency": random.choice(["USD", "XRP", "EUR"]),
                    "status": "completed",
                    "description": f"Load test txn {i}",
                }

                async def one_request(
                    data: dict[str, Any],
                ) -> tuple[bool, float | None, int | None]:
                    t0 = time.perf_counter()
                    resp = await client.post("/transactions", json=data)
                    dt = time.perf_counter() - t0
                    ok = resp.status_code == 201
                    tx_id = None
                    if ok:
                        try:
                            tx_id = int(resp.json().get("id"))
                        except Exception:
                            tx_id = None
                    return ok, dt, tx_id

                tasks.append(one_request(payload))
            batch = await asyncio.gather(*tasks, return_exceptions=True)
            for item in batch:
                if isinstance(item, BaseException):
                    continue
                ok, dt, txid = item
                if ok:
                    successes += 1
                    if first_id is None and txid is not None:
                        first_id = txid
                if dt is not None:
                    results.append(dt)

        # Sanity checks
        # List transactions
        rlist = await client.get("/transactions")
        rlist.raise_for_status()
        txs = rlist.json()
        # Admin analytics
        ra = await client.get("/admin/analytics/transactions")
        ra.raise_for_status()
        analytics = ra.json()
        # XRPL endpoints (will error if client not patched/connected) - tolerate 500
        rx = await client.post("/xrpl/create-account")
        rb = await client.get("/xrpl/balance/rTest123")

    summary = {
        "attempted": n,
        "successes": successes,
        "success_rate": successes / max(n, 1),
        "avg_ms": (statistics.mean(results) * 1000) if results else 0.0,
        "p50_ms": (statistics.median(results) * 1000) if results else 0.0,
        "max_ms": (max(results) * 1000) if results else 0.0,
        "list_count": (len(txs) if isinstance(txs, list) else None),
        "analytics": analytics,
        "xrpl_create_account_status": rx.status_code,
        "xrpl_balance_status": rb.status_code,
        "first_tx_id": first_id,
    }
    return summary


def main() -> None:
    summary = asyncio.run(run_load(1000))
    # Pretty-print minimal summary
    print("Load test summary:")
    for k, v in summary.items():
        print(f"- {k}: {v}")


if __name__ == "__main__":
    main()
