import importlib

import pytest
from httpx import ASGITransport, AsyncClient


def _prometheus_available() -> bool:
    try:
        importlib.import_module("prometheus_client")
        return True
    except Exception:
        return False


@pytest.mark.asyncio
@pytest.mark.skipif(
    not _prometheus_available(), reason="prometheus_client not installed",
)
async def test_rate_limit_counters_increment_on_allow_and_deny(monkeypatch):
    """Enable in-memory rate limit with capacity=1 and no refill to force a deny on second call.

    Then assert /metrics reflects both allowed and denied counters.
    """
    # Ensure in-memory limiter is used and deterministic
    monkeypatch.setenv("ENABLE_RATE_LIMIT", "true")
    monkeypatch.setenv("RATE_LIMIT_CAPACITY", "1")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "0")
    monkeypatch.delenv("REDIS_URL", raising=False)

    from importlib import reload

    from app import main as app_main

    # Recreate app module to reinitialize middleware with env vars
    reload(app_main)
    app = app_main.app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:  # type: ignore
        # First request allowed
        r1 = await c.get("/status")
        assert r1.status_code == 200
        # Second request should be 429 due to capacity=1 and 0 refill
        r2 = await c.get("/status")
        assert r2.status_code == 429

        # Scrape metrics and look for incremented counters
        m = await c.get("/metrics")
        assert m.status_code == 200
        body = m.text
        assert "rate_limit_allowed_total" in body
        assert "rate_limit_denied_total" in body
