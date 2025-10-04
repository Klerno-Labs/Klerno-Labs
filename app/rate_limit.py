"""Lightweight in-memory rate limiting middleware (optional).

Activated when ENABLE_RATE_LIMIT=true. This is a coarse, process-local
implementation intended as a scaffold; for production scale replace
with a distributed limiter (Redis, Memcached, etc.).
"""

from __future__ import annotations

import contextlib
import os
import threading
import time
from collections.abc import Awaitable, Callable

from fastapi import Request
from fastapi.responses import JSONResponse, Response

# Optional metrics helpers; safe to import even if metrics unavailable
try:  # pragma: no cover - import side effects tested elsewhere
    from .metrics import inc_rate_limit_allowed, inc_rate_limit_denied
except Exception:  # pragma: no cover

    def inc_rate_limit_allowed(backend: str = "memory") -> None:  # type: ignore[no-redef]
        return

    def inc_rate_limit_denied(backend: str = "memory") -> None:  # type: ignore[no-redef]
        return


class TokenBucket:
    __slots__ = ("capacity", "last_refill", "lock", "refill_rate", "tokens")

    def __init__(self, capacity: int, refill_rate: float) -> None:
        self.capacity = capacity
        self.tokens = float(capacity)
        self.refill_rate = float(refill_rate)  # tokens per second
        self.last_refill = time.perf_counter()
        self.lock = threading.Lock()

    def consume(self, amount: float = 1.0) -> bool:
        now = time.perf_counter()
        with self.lock:
            elapsed = now - self.last_refill
            if elapsed > 0:
                refill = elapsed * self.refill_rate
                if refill > 0:
                    self.tokens = min(self.capacity, self.tokens + refill)
                    self.last_refill = now
            if self.tokens >= amount:
                self.tokens -= amount
                return True
            return False


def _rate_limit_config() -> tuple[int, float]:
    cap = int(os.getenv("RATE_LIMIT_CAPACITY", "60"))  # burst
    per_minute = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))
    rate_per_sec = per_minute / 60.0
    return cap, rate_per_sec


def add_rate_limiter(app) -> None:
    if os.getenv("ENABLE_RATE_LIMIT", "false").lower() not in {"1", "true", "yes"}:
        return

    capacity, refill_rate = _rate_limit_config()
    buckets: dict[str, TokenBucket] = {}
    lock = threading.Lock()

    def get_bucket(key: str) -> TokenBucket:
        b = buckets.get(key)
        if b is None:
            with lock:
                b = buckets.get(key)
                if b is None:
                    b = TokenBucket(capacity, refill_rate)
                    buckets[key] = b
        return b

    @app.middleware("http")
    async def _apply_rate_limit(
        request: Request, call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # Never rate-limit metrics endpoint to keep observability reliable
        try:
            if request.url.path in ("/metrics", "/csp/report"):
                return await call_next(request)
        except Exception:
            pass
        # Simple key: remote IP (fall back to 'unknown')
        client_host = request.client.host if request.client else "unknown"
        bucket = get_bucket(client_host)
        allowed = bucket.consume(1.0)
        # Compute simple header values
        remaining = int(max(bucket.tokens, 0)) if allowed else 0
        reset_sec = 1  # coarse estimate; precise reset depends on token math
        base_headers = {
            "X-RateLimit-Limit": str(int(bucket.capacity)),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset_sec),
        }

        if not allowed:
            # Metrics: record denied
            with contextlib.suppress(Exception):
                inc_rate_limit_denied("memory")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limited",
                    "detail": "Too many requests; please slow down.",
                },
                headers={"Retry-After": str(reset_sec), **base_headers},
            )
        resp = await call_next(request)
        # Metrics: record allowed
        with contextlib.suppress(Exception):
            inc_rate_limit_allowed("memory")
        try:
            for k, v in base_headers.items():
                resp.headers.setdefault(k, v)
        except Exception:
            pass
        return resp
