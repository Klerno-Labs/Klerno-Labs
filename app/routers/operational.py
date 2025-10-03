"""Operational and infrastructure endpoints split from main application module.

Provides health, readiness, status, and utility endpoints. This modularization
reduces the size of `app.main` and prepares the codebase for future router level
middleware, versioning and dependency injection.
"""

from __future__ import annotations

import contextlib
import os
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from ..logging_config import get_logger
from ..settings import settings

logger = get_logger("routers.operational")

router = APIRouter(tags=["operational"])  # no prefix to keep legacy paths stable

# Startup time is still tracked in main; for uptime we read a timestamp that main can set.
# We fall back to import-time for safety.
START_TIME = datetime.now(UTC)
try:  # pragma: no cover - best effort import
    from ..main import START_TIME as APP_START_TIME

    START_TIME = APP_START_TIME  # noqa: N816 (keep upper case alias semantics)
except Exception:  # pragma: no cover
    # Best-effort import only: ignore failures (startup ordering in tests/ASGI)
    pass


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    uptime_seconds: float


class StatusResponse(BaseModel):
    status: str
    version: str
    environment: str


class ReadyResponse(BaseModel):
    status: str
    db: str
    uptime_seconds: float


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Liveness probe."""
    uptime = (datetime.now(UTC) - START_TIME).total_seconds()
    return HealthResponse(
        status="ok", timestamp=datetime.now(UTC).isoformat(), uptime_seconds=uptime
    )


@router.get("/healthz", response_model=HealthResponse)
async def healthz_check() -> HealthResponse:
    """Alias kept for backwards compatibility."""
    return await health_check()


@router.get("/status", response_model=StatusResponse)
async def status() -> StatusResponse:
    return StatusResponse(
        status="running", version="1.0.0", environment=settings.environment
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
                status="not_ready", db=db_status, uptime_seconds=uptime
            ).model_dump(),
        )
    return ReadyResponse(status="ready", db=db_status, uptime_seconds=uptime)


@router.get("/favicon.ico")
async def favicon() -> Any:
    return FileResponse("static/klerno-logo.png", media_type="image/png")


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
async def csp_report(report: dict[str, Any] | None = None) -> Any:
    """Receive CSP violation reports (report-only mode).

    For now we log and ack; future work could persist or aggregate metrics.
    """
    try:  # pragma: no cover - logging only
        if report:
            logger.info("csp.violation", report=report)
    except Exception:
        logger.debug("csp.report_log_failed", exc_info=True)
    return {"ok": True}
