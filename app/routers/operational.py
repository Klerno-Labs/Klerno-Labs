"""Operational and infrastructure endpoints split from main application module.

Provides health, readiness, status, and utility endpoints. This modularization
reduces the size of `app.main` and prepares the codebase for future router level
middleware, versioning and dependency injection.
"""

from __future__ import annotations

import contextlib
import os
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from ..logging_config import get_logger
from ..metrics import inc_csp_violation  # safe no-op if metrics disabled
from ..settings import settings

logger = get_logger("routers.operational")

router = APIRouter(tags=["operational"])  # no prefix to keep legacy paths stable

# Startup time is still tracked in main; for uptime we read a timestamp that main can set.
# We fall back to import-time for safety.
START_TIME = datetime.now(UTC)
try:  # pragma: no cover - best effort import
    from ..main import START_TIME as APP_START_TIME

    START_TIME = APP_START_TIME
except Exception:  # pragma: no cover
    # Best-effort import only: ignore failures (startup ordering in tests/ASGI)
    pass

# In-memory ring buffer for recent CSP violation reports
# Keep it small to avoid memory bloat; this is only for quick diagnostics.
CSP_REPORTS: deque[dict[str, Any]] = deque(maxlen=200)


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    uptime_seconds: float


class StatusResponse(BaseModel):
    status: str
    version: str
    environment: str


class StatusDetailsResponse(StatusResponse):
    strict_auth_transactions: bool
    rate_limit_enabled: bool
    metrics_mode: str
    request_id_enabled: bool
    request_id_header: str


class ReadyResponse(BaseModel):
    status: str
    db: str
    uptime_seconds: float


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Liveness probe."""
    uptime = (datetime.now(UTC) - START_TIME).total_seconds()
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(UTC).isoformat(),
        uptime_seconds=uptime,
    )


@router.get("/healthz", response_model=HealthResponse)
async def healthz_check() -> HealthResponse:
    """Alias kept for backwards compatibility."""
    return await health_check()


@router.get("/status", response_model=StatusResponse)
async def status() -> StatusResponse:
    return StatusResponse(
        status="running",
        version="1.0.0",
        environment=settings.environment,
    )


@router.get("/status/details", response_model=StatusDetailsResponse)
async def status_details() -> StatusDetailsResponse:
    # Strict auth toggle via environment variable
    strict_auth = os.getenv("STRICT_AUTH_TRANSACTIONS", "").lower() in {
        "1",
        "true",
        "yes",
    }

    # Rate limit enabled via env
    rl = os.getenv("ENABLE_RATE_LIMIT", "").strip().lower() in {"1", "true", "yes"}

    # Metrics mode: check if prometheus_client import works
    try:
        __import__("prometheus_client")
        metrics_mode = "prometheus"
    except Exception:
        metrics_mode = "fallback"

    return StatusDetailsResponse(
        status="running",
        version="1.0.0",
        environment=settings.environment,
        strict_auth_transactions=strict_auth,
        rate_limit_enabled=rl,
        metrics_mode=metrics_mode,
        request_id_enabled=True,
        request_id_header="X-Request-ID",
    )


@router.get("/ready", response_model=ReadyResponse)
async def readiness() -> ReadyResponse | JSONResponse:
    """Readiness probe verifying DB connectivity."""
    uptime = (datetime.now(UTC) - START_TIME).total_seconds()
    db_status = "ok"
    try:
        from .. import store

        con = store._conn()
        with contextlib.suppress(Exception):
            cur = con.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
        with contextlib.suppress(Exception):
            con.close()
    except Exception:
        db_status = "error"

    if db_status != "ok":
        return JSONResponse(
            status_code=503,
            content=ReadyResponse(
                status="not_ready",
                db=db_status,
                uptime_seconds=uptime,
            ).model_dump(),
        )
    return ReadyResponse(status="ready", db=db_status, uptime_seconds=uptime)


@router.get("/favicon.ico")
async def favicon(request: Request) -> Any:
    """Serve PNG favicon with ETag and Cache-Control, supporting 304.

    Returns project logo if present, else a 1x1 transparent PNG.
    """
    from base64 import b64decode
    from hashlib import md5

    headers: dict[str, str] = {"Cache-Control": "public, max-age=86400"}

    icon_path = "static/klerno-logo.png"
    if Path(icon_path).exists():
        try:
            with Path(icon_path).open("rb") as f:
                content = f.read()
            etag = md5(content, usedforsecurity=False).hexdigest()  # nosec: B324 - ETag generation only
            headers["ETag"] = etag
            inm = request.headers.get("if-none-match")
            if inm and inm.strip('"') == etag:
                return Response(status_code=304, headers=headers)
            return Response(content=content, media_type="image/png", headers=headers)
        except Exception:
            pass  # fall through to transparent icon

    # 1x1 transparent PNG fallback
    transparent_png = b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
    )
    etag = md5(transparent_png, usedforsecurity=False).hexdigest()  # nosec: B324 - ETag generation only
    headers["ETag"] = etag
    inm = request.headers.get("if-none-match")
    if inm and inm.strip('"') == etag:
        return Response(status_code=304, headers=headers)
    return Response(content=transparent_png, media_type="image/png", headers=headers)


@router.post("/dev/bootstrap", include_in_schema=False)
async def dev_bootstrap() -> Any:
    from .. import store

    if getattr(settings, "environment", "development") == "production":
        raise HTTPException(status_code=404, detail="Not available")

    email = os.getenv("DEV_ADMIN_EMAIL", "klerno@outlook.com")
    password = os.getenv("DEV_ADMIN_PASSWORD", "Labs2025")

    with contextlib.suppress(Exception):
        store.init_db()

    existing = store.get_user_by_email(email)
    if existing:
        return {"ok": True, "message": f"admin exists: {existing.get('email')}"}

    try:
        from ..security_session import hash_pw

        pw_hash = hash_pw(password)
        user = store.create_user(
            email=email,
            password_hash=pw_hash,
            role="admin",
            subscription_active=True,
        )
        return {
            "ok": True,
            "created": True,
            "email": (user.get("email") if user else None),
        }
    except Exception as e:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/csp/report", include_in_schema=False)
async def csp_report(request: Request, report: dict[str, Any] | None = None) -> Any:
    """Receive CSP violation reports (report-only mode).

    For now we log and ack; future work could persist or aggregate metrics.
    """
    payload: dict[str, Any] | None = None
    try:
        # Some UAs send application/reports+json (array), others application/csp-report (object)
        if report:
            payload = report
        else:  # try to parse raw body
            data = await request.json()
            if isinstance(data, list) and data:
                # Take the first entry for simplicity
                payload = data[0]
            elif isinstance(data, dict):
                payload = data
    except Exception:
        payload = None

    try:  # pragma: no cover - logging only
        meta = {
            "ts": datetime.now(UTC).isoformat(),
            "ua": request.headers.get("user-agent", ""),
            "ip": request.client.host if request.client else None,
        }
        entry = {"report": payload, **meta}
        CSP_REPORTS.append(entry)
        logger.info("csp.violation", **meta, report=payload)
        # Extract effective directive and increment metrics
        if payload:
            body = payload.get("csp-report") or payload.get("body") or payload
            directive = (
                body.get("effectiveDirective")
                or body.get("violated-directive")
                or body.get("directive")
            )
            inc_csp_violation(directive or "unknown")
    except Exception:
        logger.debug("csp.report_log_failed", exc_info=True)
    return {"ok": True}


@router.get("/csp/recent", include_in_schema=False)
async def csp_recent(limit: int = 50) -> Any:
    """Return recent CSP violation reports (most recent first)."""
    try:
        lim = max(1, min(int(limit), len(CSP_REPORTS) or 0, 200))
    except Exception:
        lim = min(50, len(CSP_REPORTS) or 0)
    if lim == 0:
        return []
    # Convert to list and return newest first
    return list(CSP_REPORTS)[-lim:][::-1]
