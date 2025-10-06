from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Header

from .authz import Tier, require_min_tier_env

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/access")
async def admin_access(
    x_user_tier: str | None = Header(default=None, alias="X-User-Tier"),
    _tier: Tier = Depends(require_min_tier_env("ADMIN_PAGE_MIN_TIER", "admin")),
) -> dict[str, object]:
    """Admin access JSON: shows gating config and detected tier."""
    gating_enabled = str(os.getenv("ENABLE_TIER_GATING", "false")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    return {
        "gating_enabled": gating_enabled,
        "defaults": {
            "DEFAULT_USER_TIER": os.getenv("DEFAULT_USER_TIER"),
            "TOKEN_STATUS_MIN_TIER": os.getenv("TOKEN_STATUS_MIN_TIER", "admin"),
            "NEON_PROXY_MIN_TIER": os.getenv("NEON_PROXY_MIN_TIER", "premium"),
            "ADMIN_PAGE_MIN_TIER": os.getenv("ADMIN_PAGE_MIN_TIER", "admin"),
        },
        "detected": {
            "current_tier": (
                (x_user_tier or os.getenv("DEFAULT_USER_TIER") or "free")
                .strip()
                .lower()
            ),
        },
        "notes": [
            "Set ENABLE_TIER_GATING=true to enforce minimum tiers.",
            "Use X-User-Tier header per request to simulate customer tier.",
        ],
    }


# Minimal admin module by design: focused and dependency-free.
