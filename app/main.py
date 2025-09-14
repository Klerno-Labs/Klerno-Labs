# ==============================================================================
# Klerno Labs - Main Application
# ==============================================================================
# This Python script has been rewritten for clarity and to ensure no conflicts.
# It merges logic cleanly, removes redundant code, and organizes imports and 
# functionality in a structured manner.

from __future__ import annotations

import asyncio
import hmac
import os
import secrets
from collections.abc import Awaitable, Callable
from dataclasses import asdict, fields as dc_fields, is_dataclass
from datetime import datetime, timedelta
from io import StringIO
from typing import Any

import pandas as pd
from fastapi import (
    Body,
    Depends,
    FastAPI,
    Form,
    Header,
    HTTPException,
    Request,
    Security,
    WebSocket,
)
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.gzip import GZipMiddleware

# Fast JSON (fallback to default if ORJSON not installed)
try:
    from fastapi.responses import ORJSONResponse as FastJSON

    DEFAULT_RESP_CLS = FastJSON
except ImportError:
    FastJSON = JSONResponse
    DEFAULT_RESP_CLS = JSONResponse

# Importing modules
from . import auth as auth_router
from . import paywall_hooks as paywall_hooks
from . import store
from .admin import router as admin_router
from .compliance import tag_category
from .deps import require_paid_or_admin, require_user
from .guardian import score_risk
from .integrations.xrp import fetch_account_tx, xrpl_json_to_transactions
from .models import ReportRequest, TaggedTransaction, Transaction
from .reporter import csv_export, summary
from .routes.analyze_tags import router as analyze_tags_router
from .security import enforce_api_key, expected_api_key
from .security_session import hash_pw, issue_jwt, verify_pw

# ---------- Optional LLM helpers ----------
try:
    from .llm import apply_filters as _llm_apply_filters
    from .llm import (
        ask_to_filters,
        explain_batch,
        explain_selection,
        explain_tx,
        summarize_rows,
    )
except ImportError:
    from .llm import (
        ask_to_filters,
        explain_batch,
        explain_selection,
        explain_tx,
        summarize_rows,
    )
    _llm_apply_filters = None


# ==============================================================================
# Utility Functions
# ==============================================================================

def _apply_filters_safe(rows: list[dict[str, Any]], spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Fallback if llm.apply_filters isn't available."""
    if _llm_apply_filters:
        return _llm_apply_filters(rows, spec)
    if not spec:
        return rows
    out = rows
    for k, v in spec.items():
        # Handle numeric/date operators
        if k in ("min_amount", "max_amount"):
            key = "amount"
            if k == "min_amount":
                out = [r for r in out if float(r.get(key, 0) or 0) >= float(v)]
            else:
                out = [r for r in out if float(r.get(key, 0) or 0) <= float(v)]
            continue
        if k in ("date_from", "date_to"):
            try:
                dt_key = "timestamp"
                if k == "date_from":
                    out = [r for r in out if _safe_dt(r.get(dt_key)) >= _safe_dt(v)]
                else:
                    out = [r for r in out if _safe_dt(r.get(dt_key)) <= _safe_dt(v)]
            except Exception:
                pass
            continue
        out = [r for r in out if str(r.get(k, "")).lower() == str(v).lower()]
    return out


def _dump(obj: Any) -> dict[str, Any]:
    """Return a dict from either a Pydantic model or a dataclass."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if is_dataclass(obj):
        return asdict(obj)
    try:
        return dict(obj)
    except Exception:
        return {"value": obj}


def _safe_dt(x) -> datetime:
    """Parse a datetime safely."""
    try:
        return datetime.fromisoformat(str(x).replace("Z", ""))
    except Exception:
        return datetime.min


def _risk_bucket(score: float) -> str:
    """Categorize risk score into buckets."""
    s = float(score or 0)
    if s < 0.33:
        return "low"
    if s < 0.66:
        return "medium"
    return "high"


def _row_score(r: dict[str, Any]) -> float:
    """NaN-safe getter for risk score."""
    try:
        val = r.get("score", None)
        if val is None or (isinstance(val, float) and pd.isna(val)):
            val = r.get("risk_score", 0)
        if isinstance(val, float) and pd.isna(val):
            val = 0
        return float(val or 0)
    except Exception:
        return 0.0


# ==============================================================================
# Security Middleware
# ==============================================================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce security headers."""

    def __init__(self, app):
        super().__init__(app)
        self.enable_hsts = os.getenv("ENABLE_HSTS", "true").lower() == "true"

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[HTMLResponse]]):
        resp = await call_next(request)
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data:; "
            "font-src 'self' data: https://cdn.jsdelivr.net; "
            "connect-src 'self' ws: wss:; "
            "object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
        )
        resp.headers.setdefault("Content-Security-Policy", csp)
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resp.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if self.enable_hsts and request.url.scheme == "https":
            resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains; preload")
        return resp


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to assign request IDs."""

    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or secrets.token_hex(8)
        request.state.request_id = rid
        resp = await call_next(request)
        resp.headers.setdefault("X-Request-ID", rid)
        return resp


# ==============================================================================
# FastAPI Application Setup
# ==============================================================================

# Application setup
app = FastAPI(
    title="Klerno Labs API (MVP) — XRPL First",
    default_response_class=DEFAULT_RESP_CLS,
)

# Middleware
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=512)

# Static files and templates
BASE_DIR = os.path.dirname(__file__)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
templates.env.globals["url_path_for"] = app.url_path_for

# Include routers
app.include_router(auth_router.router)
app.include_router(paywall_hooks.router)
app.include_router(analyze_tags_router)
app.include_router(admin_router)

# Database initialization
store.init_db()

# Additional functionality (e.g., WebSocket, APIs, etc.) will be defined below.
# ==============================================================================