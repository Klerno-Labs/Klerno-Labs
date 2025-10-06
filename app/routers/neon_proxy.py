from __future__ import annotations

import os
import time
from typing import Any, cast

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException

from app.authz import Tier, require_min_tier_env
from app.models import NeonRow, TokenStatus

try:
    from app.metrics import neon_record
except Exception:  # pragma: no cover

    def neon_record(route: str, status: int, duration: float) -> None:
        return


router = APIRouter(prefix="/api/neon", tags=["neon-data-api"])


def _base_url() -> str:
    """Resolve Neon Data API base URL from env at call time.

    This allows tests to monkeypatch env and ensures latest values are used.
    """
    url = os.getenv("VITE_NEON_DATA_API_URL", os.getenv("NEON_DATA_API_URL", ""))
    return url.rstrip("/") if url else ""


def _auth_header(authorization: str | None) -> dict[str, str]:
    # Prefer incoming Authorization header, fall back to NEON_API_KEY env
    if authorization and authorization.lower().startswith("bearer "):
        return {"Authorization": authorization}
    token = os.getenv("NEON_API_KEY")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def _decode_jwt(token: str) -> dict[str, Any] | None:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        import base64
        import json

        def b64url_decode(data: str) -> bytes:
            padding = "=" * (-len(data) % 4)
            return base64.urlsafe_b64decode(data + padding)

        header = json.loads(b64url_decode(parts[0]))
        payload = json.loads(b64url_decode(parts[1]))
        return {"header": header, "payload": payload}
    except Exception:
        return None


@router.get("/token-status")
async def token_status(
    Authorization: str | None = Header(default=None),
    _tier: Tier = Depends(require_min_tier_env("TOKEN_STATUS_MIN_TIER", "admin")),
) -> TokenStatus:
    """Quick status for Neon token from header or env.

    Returns:
      - source: "header" | "env" | "missing"
      - is_jwt: bool
      - claims: subset of payload claims if decodable
      - base_url_configured: bool
    """
    src = "missing"
    token: str | None = None
    if Authorization and Authorization.lower().startswith("bearer "):
        token = Authorization.split(" ", 1)[1]
        src = "header"
    elif os.getenv("NEON_API_KEY"):
        token = os.getenv("NEON_API_KEY")
        src = "env"

    info: dict[str, Any] = {
        "source": src,
        "base_url_configured": bool(_base_url()),
        "is_jwt": False,
    }
    if token:
        info["is_jwt"] = token.count(".") == 2
        decoded = _decode_jwt(token)
        if decoded and isinstance(decoded.get("payload"), dict):
            payload = decoded["payload"]
            claims = {
                k: payload.get(k) for k in ("iss", "aud", "sub", "role", "exp", "iat")
            }
            info["claims"] = claims
            # Expiry helpers
            try:
                exp = payload.get("exp")
                if isinstance(exp, (int, float)):
                    now = time.time()
                    seconds = int(exp - now)
                    info["seconds_to_expiry"] = seconds
                    threshold = int(os.getenv("NEON_NEAR_EXPIRY_SECONDS", "300"))
                    info["near_expiry"] = seconds <= threshold
            except Exception:
                pass
    return cast(TokenStatus, info)


@router.get("/notes")
async def list_notes(
    Authorization: str | None = Header(default=None),
    _tier: Tier = Depends(require_min_tier_env("NEON_PROXY_MIN_TIER", "premium")),
) -> list[NeonRow]:
    base = _base_url()
    if not base:
        raise HTTPException(status_code=500, detail="Neon Data API URL not configured")
    url = f"{base}/notes?select=*&limit=10"
    headers = {"Accept": "application/json"}
    headers.update(_auth_header(Authorization))
    async with httpx.AsyncClient(timeout=15) as client:
        import time as _t

        _start = _t.perf_counter()
        try:
            r = await client.get(url, headers=headers)
        except httpx.RequestError as e:
            neon_record("notes", 500, _t.perf_counter() - _start)
            raise HTTPException(
                status_code=500,
                detail=f"Neon Data API connection error: {e.__class__.__name__}",
            ) from e
        if r.status_code == 401:
            neon_record("notes", 401, _t.perf_counter() - _start)
            raise HTTPException(status_code=401, detail="Unauthorized to Neon Data API")
        if r.status_code >= 400:
            neon_record("notes", r.status_code, _t.perf_counter() - _start)
            raise HTTPException(status_code=r.status_code, detail=r.text)
        neon_record("notes", r.status_code, _t.perf_counter() - _start)
    return r.json()


@router.get("/paragraphs")
async def list_paragraphs(
    Authorization: str | None = Header(default=None),
    _tier: Tier = Depends(require_min_tier_env("NEON_PROXY_MIN_TIER", "premium")),
) -> list[NeonRow]:
    base = _base_url()
    if not base:
        raise HTTPException(status_code=500, detail="Neon Data API URL not configured")
    url = f"{base}/paragraphs?select=*&limit=10"
    headers = {"Accept": "application/json"}
    headers.update(_auth_header(Authorization))
    async with httpx.AsyncClient(timeout=15) as client:
        import time as _t

        _start = _t.perf_counter()
        try:
            r = await client.get(url, headers=headers)
        except httpx.RequestError as e:
            neon_record("paragraphs", 500, _t.perf_counter() - _start)
            raise HTTPException(
                status_code=500,
                detail=f"Neon Data API connection error: {e.__class__.__name__}",
            ) from e
        if r.status_code == 401:
            neon_record("paragraphs", 401, _t.perf_counter() - _start)
            raise HTTPException(status_code=401, detail="Unauthorized to Neon Data API")
        if r.status_code >= 400:
            neon_record("paragraphs", r.status_code, _t.perf_counter() - _start)
            raise HTTPException(status_code=r.status_code, detail=r.text)
        neon_record("paragraphs", r.status_code, _t.perf_counter() - _start)
    return r.json()
