"""Redis-backed rate limiting middleware.

If ENABLE_RATE_LIMIT=true and REDIS_URL is set, this middleware provides a
simple token bucket / leaky bucket hybrid using Redis atomic Lua script so that
all app instances share the limit. Falls back silently if Redis is unreachable
so availability is preferred over strict enforcement.

Environment variables:
- ENABLE_RATE_LIMIT=true          Activate limiter.
- REDIS_URL=redis://host:port/0   Redis connection URL.
- RATE_LIMIT_CAPACITY=60          Burst size (bucket capacity).
- RATE_LIMIT_PER_MINUTE=120       Sustained refill rate.
- RATE_LIMIT_PREFIX=klerno:rl     Key namespace prefix.

This design avoids per-request round trips beyond a single EVALSHA (or EVAL on
first use). The Lua script stores a floating token count and last timestamp in
Unix ms. It refills tokens based on elapsed time and the configured rate.
"""

from __future__ import annotations

import os
import time
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse, Response

from ._typing_shims import IRedisLike

redis: Any | None = None
try:  # pragma: no cover - optional dependency
    import redis as _redis

    redis = _redis
except Exception:  # pragma: no cover
    redis = None

_LUA_SCRIPT = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2]) -- tokens per second
local now_ms = tonumber(ARGV[3])
local cost = tonumber(ARGV[4])

local data = redis.call('HMGET', key, 'tokens', 'ts')
local tokens = tonumber(data[1])
local ts = tonumber(data[2])
if tokens == nil then
  tokens = capacity
  ts = now_ms
else
  if now_ms > ts then
    local elapsed = (now_ms - ts) / 1000.0
    local refill = elapsed * refill_rate
    if refill > 0 then
      tokens = math.min(capacity, tokens + refill)
      ts = now_ms
    end
  end
end
local allowed = 0
if tokens >= cost then
  tokens = tokens - cost
  allowed = 1
end
redis.call('HMSET', key, 'tokens', tokens, 'ts', ts)
-- set TTL slightly above theoretical full refill time to expire idle buckets
local ttl = math.ceil(math.max(30, capacity / refill_rate * 2))
redis.call('EXPIRE', key, ttl)
return {allowed, tokens}
"""

_script_sha: str | None = None


def _redis_client() -> IRedisLike | None:  # pragma: no cover - trivial
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    if not redis:
        return None
    try:
        return redis.Redis.from_url(url, decode_responses=False)
    except Exception:
        return None


def _rate_limit_config() -> tuple[int, float, str]:
    capacity = int(os.getenv("RATE_LIMIT_CAPACITY", "60"))
    per_minute = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))
    rate_per_sec = per_minute / 60.0
    prefix = os.getenv("RATE_LIMIT_PREFIX", "klerno:rl")
    return capacity, rate_per_sec, prefix


def add_redis_rate_limiter(app: Any) -> None:
    if os.getenv("ENABLE_RATE_LIMIT", "false").lower() not in {"1", "true", "yes"}:
        return
    if not os.getenv("REDIS_URL"):
        return  # prefer existing in-memory limiter path
    client = _redis_client()
    if not client:
        return
    capacity, rate_per_sec, prefix = _rate_limit_config()
    cost = 1.0

    def _eval_bucket(remote: str) -> bool:
        global _script_sha
        key = f"{prefix}:{remote}"
        now_ms = int(time.time() * 1000)
        # Redis-py eval / evalsha expects keys + args lists; we'll keep simple order
        keys: list[str] = [key]
        args: list[Any] = [capacity, rate_per_sec, now_ms, cost]
        try:  # pragma: no cover - network integration
            if _script_sha is None:
                _script_sha = client.script_load(_LUA_SCRIPT)
                res = client.evalsha(_script_sha, len(keys), *keys, *args)
        except Exception:
            try:
                res = client.eval(_LUA_SCRIPT, len(keys), *keys, *args)
                _script_sha = None
            except Exception:
                return True  # fail-open (do not block traffic)
        try:
            allowed_flag = int(res[0]) if res else 0
        except Exception:
            return True  # fail-open on unexpected structure
        return allowed_flag == 1

    @app.middleware("http")
    async def _redis_rate_limit(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        remote = request.client.host if request.client else "unknown"
        allowed = _eval_bucket(remote)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limited",
                    "detail": "Too many requests; please slow down.",
                },
                headers={"Retry-After": "1"},
            )
        return await call_next(request)
