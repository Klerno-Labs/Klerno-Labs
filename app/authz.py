from __future__ import annotations

import os
from collections.abc import Awaitable, Callable
from enum import IntEnum

from fastapi import Header, HTTPException


class Tier(IntEnum):
    free = 0
    pro = 1
    premium = 2
    admin = 3


def parse_tier(value: str | None) -> Tier:
    if not value:
        return Tier.free
    v = str(value).strip().lower()
    if v not in {"free", "pro", "premium", "admin"}:
        return Tier.free
    return Tier[v]


def _is_truthy(val: str | None) -> bool:
    return str(val).strip().lower() in {"1", "true", "yes", "on"}


def require_min_tier_env(
    env_var: str, default: str
) -> Callable[[str | None], Awaitable[Tier]]:
    """Create a dependency that enforces a minimum tier based on an env var.

    - Reads required tier from os.getenv(env_var) or provided default.
    - Extracts the current user's tier from header X-User-Tier, falling back to DEFAULT_USER_TIER.
    - Raises 403 if current tier < required tier.
    """

    async def _dep(x_user_tier: str | None = Header(default=None)) -> Tier:
        required_str = os.getenv(env_var, default)
        required = parse_tier(required_str)
        current = parse_tier(x_user_tier or os.getenv("DEFAULT_USER_TIER"))
        # Feature flag: only enforce when enabled
        if _is_truthy(os.getenv("ENABLE_TIER_GATING", "false")) and current < required:
            raise HTTPException(
                status_code=403, detail="Insufficient tier for this endpoint"
            )
        return current

    return _dep
