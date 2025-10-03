"""Refresh token issuance, storage (in-memory / optional Redis), and rotation.

Environment variables:
- REFRESH_TOKEN_TTL_DAYS (default 7)
- REFRESH_TOKEN_LENGTH (default 48)
- USE_REDIS_REFRESH=true to store in Redis instead of in-process memory.

Fail-safe: if Redis errors occur we fall back to in-memory ephemeral store.

Security model:
- Each refresh token is single-use; on refresh we revoke the old token and issue
  a new pair (access + refresh).
- Revocation list[Any] keeps used tokens until natural TTL.
- Access tokens remain short-lived (configured via existing ACCESS_TOKEN_EXPIRE_MINUTES).
"""

from __future__ import annotations

import os
import secrets
import time
from dataclasses import dataclass
from typing import Any

from .settings import settings

# runtime-optional redis client (may be absent in dev/test envs)
redis: Any | None = None
try:  # pragma: no cover - optional
    import redis as _redis

    redis = _redis
except Exception:  # pragma: no cover
    redis = None


@dataclass
class RefreshRecord:
    user_id: int
    email: str
    role: str
    expires_at: float


# In-memory fallback stores
_store: dict[str, RefreshRecord] = {}
_revoked: set[str] = set()

_REFRESH_PREFIX = "klerno:rt"


def _ttl_seconds() -> int:
    days = getattr(settings, "refresh_token_expire_days", 7)
    return days * 86400


def _token_len() -> int:
    return int(os.getenv("REFRESH_TOKEN_LENGTH", "48"))


def _redis_client() -> None:  # pragma: no cover
    if os.getenv("USE_REDIS_REFRESH", "false").lower() not in {"1", "true", "yes"}:
        return None
    url = os.getenv("REDIS_URL")
    if not url or not redis:
        return None
    try:
        return redis.Redis.from_url(url, decode_responses=False)
    except Exception:
        return None


def _generate_refresh() -> str:
    raw = secrets.token_urlsafe(_token_len())
    return raw


def issue_refresh(user_id: int, email: str, role: str) -> str:
    token = _generate_refresh()
    exp = time.time() + _ttl_seconds()
    rec = RefreshRecord(user_id=user_id, email=email, role=role, expires_at=exp)
    client = _redis_client()
    if client:
        try:  # store as hash
            key = f"{_REFRESH_PREFIX}:{token}"
            client.hset(
                key,
                mapping={"uid": user_id, "email": email, "role": role, "exp": int(exp)},
            )
            client.expire(key, _ttl_seconds())
            return token
        except Exception:
            pass
    _store[token] = rec
    return token


def revoke_refresh(token: str) -> None:
    _revoked.add(token)
    client = _redis_client()
    if client:
        with client.pipeline() as p:  # pragma: no cover
            try:
                p.delete(f"{_REFRESH_PREFIX}:{token}")
                p.sadd(f"{_REFRESH_PREFIX}:revoked", token)
                p.execute()
            except Exception:
                pass


def validate_refresh(token: str) -> RefreshRecord | None:
    if token in _revoked:
        return None
    client = _redis_client()
    if client:
        try:
            key = f"{_REFRESH_PREFIX}:{token}"
            data = client.hgetall(key)
            if not data:
                return None
            # Redis returns bytes keys/values
            b = {k.decode(): v.decode() for k, v in data.items()}
            exp = float(b.get("exp", "0"))
            if exp < time.time():
                return None
            return RefreshRecord(
                user_id=int(b["uid"]),
                email=b["email"],
                role=b.get("role", "user"),
                expires_at=exp,
            )
        except Exception:
            pass
    rec = _store.get(token)
    if not rec:
        return None
    if rec.expires_at < time.time():
        return None
    return rec


def rotate_refresh(old_token: str, user_id: int, email: str, role: str) -> str:
    revoke_refresh(old_token)
    return issue_refresh(user_id, email, role)
