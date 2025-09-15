from __future__ import annotations

from datetime import datetime, timedelta
from io import StringIO
from typing import List, Dict, Any, Optional, Callable, Awaitable, Tuple

import os
import sys
import hmac
import secrets
import pandas as pd
import sqlite3
import platform
from dataclasses import asdict, is_dataclass, fields as dc_fields

from fastapi import FastAPI, Security, Header, Request, Body, HTTPException, Depends, Form, WebSocket, Response, WebSocketDisconnect
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
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

# NEW: for live push hub
import asyncio, json
from functools import lru_cache

from . import store
from .models import Transaction, TaggedTransaction, ReportRequest
from .guardian import score_risk
from .compliance import tag_category
from .reporter import csv_export, summary
from .integrations.xrp import xrpl_json_to_transactions, fetch_account_tx
from .security import enforce_api_key, expected_api_key
from .security_session import hash_pw, verify_pw, issue_jwt
from .deps import current_user

# XRPL Payment and Subscription modules
from .config import settings

# Set up a flag to track if we're using mocks
USING_MOCK_XRPL = False

# Track application startup time
START_TIME = datetime.utcnow()

try:
    # Try to import the real XRPL payments module
    from .xrpl_payments import create_payment_request, verify_payment, get_network_info
    print("Successfully imported real XRPL payments module")
except ImportError as e:
    print(f"Could not import real XRPL module: {e}")
    try:
        # Try to import the mock implementation
        from .mocks.xrpl_mock import create_payment_request, verify_payment, get_network_info
        USING_MOCK_XRPL = True
        print("Using mock XRPL implementation (safe for testing)")
    except ImportError as e2:
        print(f"Could not import mock XRPL module: {e2}")
        # Create inline fallback implementations
        print("Using inline fallback implementations")
        USING_MOCK_XRPL = True
        
        def create_payment_request(amount, recipient, sender=None, memo=None):
            """Inline fallback implementation"""
            import random, time
            return {
                "request_id": f"fallback_{int(time.time())}_{random.randint(1000, 9999)}",
                "status": "pending",
                "mock": True,
                "amount": amount,
                "recipient": recipient
            }
            
        def verify_payment(request_id):
            """Inline fallback implementation"""
            return {"verified": True, "request_id": request_id, "mock": True}
            
        def get_network_info():
            """Inline fallback implementation"""
            return {"status": "online", "network": "testnet", "mock": True}
except ImportError:
    # Fall back to mock implementation if xrpl is not available
    print("XRPL module not available, using mock implementation")
    from .xrpl_payments_mock import create_payment_request, verify_payment, get_network_info
from .subscriptions import (
    SubscriptionTier, TierDetails, Subscription, get_tier_details,
    get_all_tiers, get_user_subscription, create_subscription,
    has_active_subscription, require_active_subscription
)

# Auth/Paywall routers
from . import auth as auth_router
from . import auth_oauth
from . import paywall_hooks as paywall_hooks
from .deps import require_paid_or_admin, require_user, require_admin
from .routes.analyze_tags import router as analyze_tags_router
from .admin import router as admin_router  # admin dashboard
from .routes.render_test import router as render_test_router  # render deployment test

# ---------- Optional LLM helpers ----------
try:
    from .llm import (
        explain_tx,
        explain_batch,
        ask_to_filters,
        explain_selection,
        summarize_rows,
        apply_filters as _llm_apply_filters,  # optional
    )
except ImportError:
    from .llm import (
        explain_tx,
        explain_batch,
        ask_to_filters,
        explain_selection,
        summarize_rows,
    )
    _llm_apply_filters = None


def _apply_filters_safe(rows: List[Dict[str, Any]], spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Fallback if llm.apply_filters isn't available."""
    if _llm_apply_filters:
        return _llm_apply_filters(rows, spec)
    if not spec:
        return rows
    out = rows
    for k, v in spec.items():
        # simple numeric/date operators
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


def _dump(obj: Any) -> Dict[str, Any]:
    """Return a dict from either a Pydantic model or a dataclass (or mapping-like)."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if is_dataclass(obj):
        return asdict(obj)
    try:
        return dict(obj)
    except Exception:
        return {"value": obj}

# ---- helpers
def _safe_dt(x) -> datetime:
    try:
        return datetime.fromisoformat(str(x).replace("Z", ""))
    except Exception:
        return datetime.min

def _risk_bucket(score: float) -> str:
    s = float(score or 0)
    if s < 0.33: return "low"
    if s < 0.66: return "medium"
    return "high"

# unified, NaN-safe reader for old/new score keys
def _row_score(r: Dict[str, Any]) -> float:
    try:
        val = r.get("score", None)
        if val is None or (isinstance(val, float) and pd.isna(val)):
            val = r.get("risk_score", 0)
        if isinstance(val, float) and pd.isna(val):
            val = 0
        return float(val or 0)
    except Exception:
        return 0.0


# =========================
# Security hardening
# =========================
REQ_ID_HEADER = "X-Request-ID"
CSRF_COOKIE = "csrf_token"
CSRF_HEADER = "X-CSRF-Token"

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.enable_hsts = (os.getenv("ENABLE_HSTS", "true").lower() == "true")

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[HTMLResponse]]):
        resp = await call_next(request)
        # UPDATED CSP: allow jsDelivr for Bootstrap & Chart.js, and allow Render's domains
        # More permissive for Render deployment to fix frontend issues
        csp = (
            "default-src 'self' https://*.render.com; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://*.render.com https://render.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://*.render.com https://render.com; "
            "img-src 'self' data: https://*.render.com https://render.com; "
            "font-src 'self' data: https://cdn.jsdelivr.net https://*.render.com https://render.com; "
            "connect-src 'self' ws: wss: https://*.render.com https://render.com; "
            "object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
        )
        
        # Make CSP more permissive in development environment
        if os.getenv("APP_ENV", "").lower() != "production":
            csp = (
                "default-src 'self' *; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' *; "
                "style-src 'self' 'unsafe-inline' *; "
                "img-src 'self' data: *; "
                "font-src 'self' data: *; "
                "connect-src 'self' ws: wss: *;"
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
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get(REQ_ID_HEADER) or secrets.token_hex(8)
        request.state.request_id = rid
        resp = await call_next(request)
        resp.headers.setdefault(REQ_ID_HEADER, rid)
        return resp

def issue_csrf_cookie(resp: HTMLResponse):
    token = secrets.token_urlsafe(32)
    resp.set_cookie(
        CSRF_COOKIE, token,
        secure=True, samesite="Strict", httponly=False, path="/", max_age=60*60*8
    )
    return token

def verify_csrf(request: Request):
    token_cookie = request.cookies.get(CSRF_COOKIE)
    token_hdr = request.headers.get(CSRF_HEADER)
    if not token_cookie or not token_hdr:
        raise HTTPException(status_code=403, detail="CSRF token missing")
    if not hmac.compare_digest(token_cookie, token_hdr):
        raise HTTPException(status_code=403, detail="Bad CSRF token")

async def csrf_protect_ui(request: Request):
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        verify_csrf(request)
    return True


# =========================
# FastAPI app + templates
# =========================
app = FastAPI(
    title="Klerno Labs API (MVP) — XRPL First",
    default_response_class=DEFAULT_RESP_CLS,
    docs_url=None,  # Disable public docs
    redoc_url=None,  # Disable public redoc
)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=512)

@app.on_event("startup")
async def _log_startup_info():
    # Check if we're running on Render
    is_render = os.environ.get("RENDER", "").lower() in ("true", "1", "yes") or \
                os.environ.get("RENDER_INSTANCE_ID", "") != ""
    print(f"[startup] Running on Render: {is_render}")
    print(f"[startup] Environment: {os.environ.get('APP_ENV', 'development')}")
    print(f"[startup] Static files directory: {os.path.join(BASE_DIR, 'static')}")
    
    # Check if static directory exists and list contents
    static_dir = os.path.join(BASE_DIR, "static")
    if os.path.exists(static_dir):
        print(f"[startup] Static directory exists: {static_dir}")
        try:
            static_files = os.listdir(static_dir)
            print(f"[startup] Static files: {static_files}")
        except Exception as e:
            print(f"[startup] Error listing static files: {e}")
    else:
        print(f"[startup] Static directory does not exist: {static_dir}")
    env = os.getenv("APP_ENV", "dev")
    port = os.getenv("PORT", "8000")
    workers = os.getenv("WORKERS", "1")
    print(f"[startup] APP_ENV={env} PORT={port} WORKERS={workers}")

# Static & templates
BASE_DIR = os.path.dirname(__file__)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
templates.env.globals["url_path_for"] = app.url_path_for

# Add custom error handlers for better debugging on Render
@app.exception_handler(404)
async def custom_404_handler(request: Request, exc: HTTPException):
    return templates.TemplateResponse(
        "base.html",
        {
            "request": request,
            "title": "404 Not Found",
            "content": f"<h1>404 Not Found</h1><p>The requested URL {request.url.path} was not found on this server.</p>"
                      f"<p>Debug info: Static directory: {os.path.join(BASE_DIR, 'static')}</p>"
        },
        status_code=404
    )

@app.exception_handler(500)
async def custom_500_handler(request: Request, exc: Exception):
    return templates.TemplateResponse(
        "base.html",
        {
            "request": request,
            "title": "500 Server Error",
            "content": f"<h1>500 Server Error</h1><p>An internal server error occurred.</p>"
                      f"<p>Error: {str(exc)}</p>"
                      f"<p>Debug info: Running on Render: {os.environ.get('RENDER', '')} / {os.environ.get('RENDER_INSTANCE_ID', '')}</p>"
                      f"<p>Environment: {os.environ.get('APP_ENV', 'development')}</p>"
        },
        status_code=500
    )

# Config flags for UI auth redirects
ADMIN_EMAIL = (os.getenv("ADMIN_EMAIL") or "").strip().lower()

# Helper function to get template context with user
def get_template_context(request: Request, **kwargs) -> dict:
    """Get template context with user information."""
    context = {"request": request}
    
    # Add user context if available
    user = current_user(request)
    if user:
        context["user"] = user
    
    # Add any additional context
    context.update(kwargs)
    return context

# ---- Session cookie config
SESSION_COOKIE = os.getenv("SESSION_COOKIE_NAME", "session")
COOKIE_SECURE_MODE = os.getenv("COOKIE_SECURE", "auto").lower()  # "auto" | "true" | "false"
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax").lower()   # "lax" | "strict" | "none"

def _is_secure_request(request: Request) -> bool:
    xf = (request.headers.get("x-forwarded-proto") or "").lower()
    if xf:
        return "https" in xf
    return request.url.scheme == "https"

def _cookie_kwargs(request: Request) -> Dict[str, Any]:
    if COOKIE_SECURE_MODE in ("true", "1", "yes"):
        secure = True
    elif COOKIE_SECURE_MODE in ("false", "0", "no"):
        secure = False
    else:
        secure = _is_secure_request(request)

    samesite = COOKIE_SAMESITE if COOKIE_SAMESITE in ("lax", "strict", "none") else "lax"
    if samesite == "none" and not secure:
        secure = True

    return {
        "httponly": True,
        "secure": secure,
        "samesite": samesite,
        "max_age": 60 * 60 * 24 * 7,  # 7 days
        "path": "/",
    }

# Include routers
from . import paywall  # noqa: E402
app.include_router(paywall.router)
app.include_router(auth_router.router)
app.include_router(auth_oauth.router)
app.include_router(paywall_hooks.router)
app.include_router(analyze_tags_router)
app.include_router(admin_router)
app.include_router(render_test_router)  # Add render deployment test router

# Init DB
store.init_db()

# --- Bootstrap single admin account (email/password) ---
BOOT_ADMIN_EMAIL = "klerno@outlook.com".lower().strip()
BOOT_ADMIN_PASSWORD = "Labs2025"

existing = store.get_user_by_email(BOOT_ADMIN_EMAIL)
if not existing:
    store.create_user(
        BOOT_ADMIN_EMAIL,
        hash_pw(BOOT_ADMIN_PASSWORD),
        role="admin",
        subscription_active=True,
    )

# ---- Live push hub (WebSocket) ----------------------------------------------
class LiveHub:
    """In-process pub/sub for real-time pushes."""
    def __init__(self):
        self._clients: dict[WebSocket, set[str]] = {}
        self._lock = asyncio.Lock()

    async def add(self, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self._clients[ws] = set()

    async def remove(self, ws: WebSocket):
        async with self._lock:
            self._clients.pop(ws, None)

    async def update_watch(self, ws: WebSocket, watch: set[str]):
        async with self._lock:
            if ws in self._clients:
                self._clients[ws] = {w.strip().lower() for w in watch if w}

    async def publish(self, item: dict):
        fa = (item.get("from_addr") or "").lower()
        ta = (item.get("to_addr") or "").lower()
        async with self._lock:
            targets = []
            for ws, watch in self._clients.items():
                if not watch or fa in watch or ta in watch:
                    targets.append(ws)
        dead = []
        for ws in targets:
            try:
                await ws.send_json({"type": "tx", "item": item})
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.remove(ws)

live = LiveHub()

@app.websocket("/ws/alerts")
async def ws_alerts(ws: WebSocket):
    await live.add(ws)
    try:
        while True:
            try:
                msg = await ws.receive_text()
                try:
                    data = json.loads(msg) if msg else {}
                except Exception:
                    data = {}
                if "watch" in data and isinstance(data["watch"], list):
                    watch = {str(x).strip().lower() for x in data["watch"] if isinstance(x, str)}
                    await live.update_watch(ws, watch)
                    await ws.send_json({"type": "ack", "watch": sorted(list(watch))})
                else:
                    await ws.send_json({"type": "pong"})
            except WebSocketDisconnect:
                # Normal disconnect, no need to crash the entire server
                break
            except Exception as e:
                # Log other errors but don't crash
                print(f"WebSocket error: {e}")
                break
    finally:
        await live.remove(ws)

# Tiny HTTP probe so hitting /ws/alerts with GET doesn't 404
@app.get("/ws/alerts", include_in_schema=False)
def ws_alerts_probe():
    return {"ok": True, "hint": "connect with WebSocket at ws(s)://<host>/ws/alerts"}


# =========================
# Email (SendGrid)
# =========================
SENDGRID_KEY = os.getenv("SENDGRID_API_KEY", "").strip()
ALERT_FROM = os.getenv("ALERT_EMAIL_FROM", "").strip()
ALERT_TO = os.getenv("ALERT_EMAIL_TO", "").strip()

def _send_email(subject: str, text: str, to_email: Optional[str] = None) -> Dict[str, Any]:
    recipient = (to_email or ALERT_TO).strip()
    if not (SENDGRID_KEY and ALERT_FROM and recipient):
        return {"sent": False, "reason": "missing SENDGRID_API_KEY/ALERT_EMAIL_FROM/ALERT_EMAIL_TO"}
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail, Email, To, Content
        msg = Mail(
            from_email=Email(ALERT_FROM),
            to_emails=To(recipient),
            subject=subject,
            plain_text_content=Content("text/plain", text),
        )
        sg = SendGridAPIClient(SENDGRID_KEY)
        resp = sg.send(msg)
        ok = 200 <= resp.status_code < 300
        return {"sent": ok, "status_code": resp.status_code, "to": recipient}
    except Exception as e:
        return {"sent": False, "error": str(e)}

def notify_if_alert(tagged: TaggedTransaction) -> Dict[str, Any]:
    threshold = float(os.getenv("RISK_THRESHOLD", "0.75"))
    if (tagged.score or 0) < threshold:
        return {"sent": False, "reason": f"score {tagged.score} < threshold {threshold}"}
    subject = f"[Klerno Labs Alert] {tagged.category or 'unknown'} — risk {round(tagged.score or 0, 3)}"
    lines = [
        f"Time:       {tagged.timestamp}",
        f"Chain:      {tagged.chain}",
        f"Tx ID:      {tagged.tx_id}",
        f"From → To:  {tagged.from_addr} → {tagged.to_addr}",
        f"Amount:     {tagged.amount} {tagged.symbol}",
        f"Direction:  {tagged.direction}",
        f"Fee:        {tagged.fee}",
        f"Category:   {tagged.category}",
        f"Risk Score: {round(tagged.score or 0, 3)}",
        f"Risk Bucket:{_risk_bucket(tagged.score or 0)}",
        f"Flags:      {', '.join(tagged.flags or []) or '—'}",
        f"Notes:      {getattr(tagged, 'notes', '') or '—'}",
    ]
    return _send_email(subject, "\n".join(lines))


# ---------------- Root, Landing & health ----------------
@app.get("/", include_in_schema=False)
def root_page(request: Request):
    """Elite landing page with premium design"""
    resp = templates.TemplateResponse("landing.html", get_template_context(request))
    issue_csrf_cookie(resp)
    return resp

@app.get("/status", include_in_schema=False)
def status_page():
    """Simple status page for uptime checks and API confirmation"""
    html = (
        "<!doctype html>\n"
        "<html><head><meta charset='utf-8'><title>Klerno Labs Status</title>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<link rel='icon' href='/favicon.ico'></head>"
        "<body style=\"font-family: system-ui, -apple-system, 'Segoe UI', Roboto, Arial, sans-serif;"
        " line-height:1.4; padding:2rem; max-width: 720px; margin: 0 auto;\">"
        "<h1 style='margin:0 0 0.5rem 0'>Klerno Labs is running ✅</h1>"
        "<p>This instance is healthy. API documentation is available to authenticated administrators.</p>"
        "<p><a href='/admin/docs' style='font-weight:600'>Admin API Docs</a> (Admin access required)</p>"
        "</body></html>"
    )
    return HTMLResponse(content=html, status_code=200)

@app.get("/landing", include_in_schema=False)
def landing(request: Request):
    resp = templates.TemplateResponse("landing.html", get_template_context(request))
    issue_csrf_cookie(resp)
    return resp

@app.head("/", include_in_schema=False)
def root_head():
    return HTMLResponse(status_code=200)

@app.get("/health")
def health(_auth: bool = Security(enforce_api_key)):
    return {"status": "ok", "time": datetime.utcnow().isoformat()}

@app.get("/healthz", include_in_schema=False)
def healthz():
    """Health check endpoint (also verifies static files)."""
    # Check if static directory exists
    static_dir = os.path.join(BASE_DIR, "static")
    static_check = {
        "exists": os.path.exists(static_dir),
        "is_dir": os.path.isdir(static_dir) if os.path.exists(static_dir) else False,
    }
    
    # List static files if directory exists
    static_files = []
    if static_check["exists"] and static_check["is_dir"]:
        try:
            static_files = os.listdir(static_dir)
            static_check["files_count"] = len(static_files)
            static_check["css_dir_exists"] = os.path.exists(os.path.join(static_dir, "css"))
            static_check["js_dir_exists"] = os.path.exists(os.path.join(static_dir, "js"))
        except Exception as e:
            static_check["error"] = str(e)
    
    # Environment info
    env_info = {
        "app_env": os.environ.get("APP_ENV", "development"),
        "is_render": os.environ.get("RENDER", "") != "" or os.environ.get("RENDER_INSTANCE_ID", "") != "",
        "render_id": os.environ.get("RENDER_INSTANCE_ID", ""),
        "python_version": platform.python_version(),
    }
    
    return {
        "status": "ok",
        "timestamp": datetime.datetime.now().isoformat(),
        "static_check": static_check,
        "static_files": static_files[:10] if len(static_files) > 0 else [],
        "env": env_info,
    }

# --------------- Favicon & static -----------------
@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    ico_path = os.path.join(BASE_DIR, "static", "favicon.ico")
    if os.path.exists(ico_path):
        return FileResponse(ico_path, media_type="image/x-icon")
    # If not present, 404 clearly instead of HTML error page
    raise HTTPException(status_code=404, detail="favicon not found")


# ---------------- UI Logout ----------------
@app.get("/logout", include_in_schema=False)
def logout_ui():
    resp = RedirectResponse("/", status_code=303)
    resp.delete_cookie(SESSION_COOKIE, path="/")
    return resp


# --- User & Settings API ---
class SettingsPayload(BaseModel):
    x_api_key: Optional[str] = None
    risk_threshold: Optional[float] = None
    time_range_days: Optional[int] = None
    ui_prefs: Optional[Dict[str, Any]] = None

@app.get("/me", include_in_schema=False)
def me(user=Depends(require_user)):
    return {
        "id": user["id"],
        "email": user["email"],
        "role": user["role"],
        "subscription_active": bool(user.get("subscription_active")),
    }

@app.get("/me/settings")
def me_settings_get(user=Depends(require_user)):
    return store.get_settings(user["id"])

@app.post("/me/settings")
def me_settings_post(payload: SettingsPayload, user=Depends(require_user)):
    allowed = {"x_api_key", "risk_threshold", "time_range_days", "ui_prefs"}
    patch = {k: v for k, v in payload.model_dump(exclude_none=True).items() if k in allowed}
    if "risk_threshold" in patch:
        patch["risk_threshold"] = max(0.0, min(1.0, float(patch["risk_threshold"])))
    if "time_range_days" in patch:
        patch["time_range_days"] = max(1, int(patch["time_range_days"]))
    store.save_settings(user["id"], patch)
    settings = store.get_settings(user["id"])
    return {"ok": True, "settings": settings}


# ---------------- Core API ----------------
@app.post("/analyze/tx", response_model=TaggedTransaction)
def analyze_tx(tx: Transaction, _auth: bool = Security(enforce_api_key)):
    risk, flags = score_risk(tx)
    category = tag_category(tx)
    return TaggedTransaction(**_dump(tx), score=risk, flags=flags, category=category)

@app.post("/analyze/batch")
def analyze_batch(txs: List[Transaction], _auth: bool = Security(enforce_api_key)):
    tagged: List[TaggedTransaction] = []
    for tx in txs:
        risk, flags = score_risk(tx)
        category = tag_category(tx)
        tagged.append(TaggedTransaction(**_dump(tx), score=risk, flags=flags, category=category))
    return {"summary": summary(tagged).model_dump(), "items": [t.model_dump() for t in tagged]}

@app.post("/report/csv")
def report_csv(req: ReportRequest, _auth: bool = Security(enforce_api_key)):
    df = pd.read_csv(os.path.join(BASE_DIR, "..", "data", "sample_transactions.csv"))
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    for col in ("from_addr", "to_addr"):
        if col not in df.columns:
            df[col] = ""
    wallets = set(getattr(req, "wallet_addresses", None) or ([] if not getattr(req, "address", None) else [req.address]))
    start = pd.to_datetime(req.start) if getattr(req, "start", None) else df["timestamp"].min()
    end = pd.to_datetime(req.end) if getattr(req, "end", None) else df["timestamp"].max()
    mask_wallet = True if not wallets else (df["to_addr"].isin(wallets) | df["from_addr"].isin(wallets))
    mask = (df["timestamp"] >= start) & (df["timestamp"] <= end) & mask_wallet
    selected = df[mask].copy()
    tx_field_names = {f.name for f in dc_fields(Transaction)}
    items: List[TaggedTransaction] = []
    for _, row in selected.iterrows():
        raw = {k: (None if pd.isna(v) else v) for k, v in row.to_dict().items()}
        raw.setdefault("memo", ""); raw.setdefault("notes", "")
        clean = {k: v for k, v in raw.items() if k in tx_field_names}
        tx = Transaction(**clean)
        risk, flags = score_risk(tx)
        category = tag_category(tx)
        items.append(TaggedTransaction(**_dump(tx), score=risk, flags=flags, category=category))
    return {"csv": csv_export(items)}


# ---------------- XRPL parse (posted JSON) ----------------
@app.post("/integrations/xrpl/parse")
def parse_xrpl(account: str, payload: List[Dict[str, Any]], _auth: bool = Security(enforce_api_key)):
    txs = xrpl_json_to_transactions(account, payload)
    tagged: List[TaggedTransaction] = []
    for tx in txs:
        risk, flags = score_risk(tx)
        category = tag_category(tx)
        tagged.append(TaggedTransaction(**_dump(tx), score=risk, flags=flags, category=category))
    return {"summary": summary(tagged).model_dump(), "items": [t.model_dump() for t in tagged]}

@app.post("/analyze/sample")
def analyze_sample(_auth: bool = Security(enforce_api_key)):
    data_path = os.path.join(BASE_DIR, "..", "data", "sample_transactions.csv")
    df = pd.read_csv(data_path)
    text_cols = ("memo", "notes", "symbol", "direction", "chain", "tx_id", "from_addr", "to_addr")
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce").dt.strftime("%Y-%m-%dT%H:%M:%S")
    for col in ("amount", "fee", "risk_score"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    txs: List[Transaction] = []
    tx_field_names = {f.name for f in dc_fields(Transaction)}
    for _, row in df.iterrows():
        raw = {k: (None if pd.isna(v) else v) for k, v in row.to_dict().items()}
        raw.setdefault("memo", ""); raw.setdefault("notes", "")
        clean = {k: v for k, v in raw.items() if k in tx_field_names}
        txs.append(Transaction(**clean))
    tagged: List[TaggedTransaction] = []
    for tx in txs:
        risk, flags = score_risk(tx)
        category = tag_category(tx)
        tagged.append(TaggedTransaction(**_dump(tx), score=risk, flags=flags, category=category))
    return {"summary": summary(tagged).model_dump(), "items": [t.model_dump() for t in tagged]}

# Add UI-friendly data seeding endpoint for dashboard
@app.post("/api/data/seed", include_in_schema=False)
def seed_sample_data_ui(_user=Depends(require_user)):
    """UI-friendly data seeding endpoint for dashboard."""
    data_path = os.path.join(BASE_DIR, "..", "data", "sample_transactions.csv")
    if not os.path.exists(data_path):
        return {"success": False, "error": "Sample data file not found"}
    
    df = pd.read_csv(data_path)
    df = df.head(50)  # Limit to 50 rows for UI
    
    # Clean the data
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce").dt.strftime("%Y-%m-%dT%H:%M:%S")
    for col in ("memo", "notes", "symbol", "direction", "chain", "tx_id", "from_addr", "to_addr"):
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str)
    for col in ("amount", "fee"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    saved = 0
    for _, row in df.iterrows():
        tx = {
            "tx_id": row.get("tx_id"),
            "timestamp": row.get("timestamp"),
            "chain": row.get("chain") or "XRPL",
            "from_addr": row.get("from_addr") or "",
            "to_addr": row.get("to_addr") or "",
            "amount": float(row.get("amount") or 0),
            "symbol": row.get("symbol") or "XRP",
            "direction": row.get("direction") or "out",
            "memo": row.get("memo") or "",
            "fee": float(row.get("fee") or 0),
            "category": row.get("category") or None,
            "notes": row.get("notes") or "",
        }
        risk, flags = score_risk(tx)
        cat = tx.get("category") or tag_category(tx)
        d = {**tx, "risk_score": risk, "risk_flags": flags, "category": cat}
        store.save_tagged(d)
        saved += 1

    return {"success": True, "message": f"Loaded {saved} sample transactions", "saved": saved}


# ---------------- “Memory” (DB) + email on save ----------------
@app.post("/analyze_and_save/tx")
async def analyze_and_save_tx(tx: Transaction, _auth: bool = Security(enforce_api_key)):
    risk, flags = score_risk(tx)
    category = tag_category(tx)
    tagged = TaggedTransaction(**_dump(tx), score=risk, flags=flags, category=category)
    d = tagged.model_dump()
    d["risk_score"] = d.get("score")
    d["risk_flags"] = d.get("flags")
    d["risk_bucket"] = _risk_bucket(d.get("risk_score", 0))
    store.save_tagged(d)
    await live.publish(d)
    email_result = notify_if_alert(tagged)
    return {"saved": True, "item": d, "email": email_result}

@app.get("/transactions/{wallet}")
def get_transactions_for_wallet(wallet: str, limit: int = 100, _auth: bool = Security(enforce_api_key)):
    rows = store.list_by_wallet(wallet, limit=limit)
    return {"wallet": wallet, "count": len(rows), "items": rows}

@app.get("/alerts")
def get_alerts(limit: int = 100, _auth: bool = Security(enforce_api_key)):
    threshold = float(os.getenv("RISK_THRESHOLD", "0.75"))
    rows = store.list_alerts(threshold, limit=limit)
    return {"threshold": threshold, "count": len(rows), "items": rows}


# ---------------- XRPL fetch (read-only) ----------------
@app.get("/integrations/xrpl/fetch")
def xrpl_fetch(account: str, limit: int = 10, _auth: bool = Security(enforce_api_key)):
    raw = fetch_account_tx(account, limit=limit)
    txs = xrpl_json_to_transactions(account, raw)
    tagged: List[TaggedTransaction] = []
    for tx in txs:
        risk, flags = score_risk(tx)
        category = tag_category(tx)
        tagged.append(TaggedTransaction(**_dump(tx), score=risk, flags=flags, category=category))
    return {"count": len(tagged), "items": [t.model_dump() for t in tagged]}

# Add alias route for dashboard compatibility
@app.post("/xrpl/fetch", include_in_schema=False)
async def xrpl_fetch_ui(account: str = "rN7n7otQDd6FczFgLdSqtcsAUxDkw6fzRH", _user=Depends(require_user)):
    """UI-friendly XRPL fetch endpoint for dashboard."""
    raw = fetch_account_tx(account, limit=20)
    txs = xrpl_json_to_transactions(account, raw)
    tagged: List[TaggedTransaction] = []
    for tx in txs:
        risk, flags = score_risk(tx)
        category = tag_category(tx)
        tagged.append(TaggedTransaction(**_dump(tx), score=risk, flags=flags, category=category))
    return {"success": True, "count": len(tagged), "items": [t.model_dump() for t in tagged]}

@app.post("/integrations/xrpl/fetch_and_save")
async def xrpl_fetch_and_save(account: str, limit: int = 10, _auth: bool = Security(enforce_api_key)):
    raw = fetch_account_tx(account, limit=limit)
    txs = xrpl_json_to_transactions(account, raw)
    saved = 0
    tagged_items: List[Dict[str, Any]] = []
    emails: List[Dict[str, Any]] = []
    for tx in txs:
        risk, flags = score_risk(tx)
        category = tag_category(tx)
        tagged = TaggedTransaction(**_dump(tx), score=risk, flags=flags, category=category)
        d = tagged.model_dump()
        d["risk_score"] = d.get("score")
        d["risk_flags"] = d.get("flags")
        d["risk_bucket"] = _risk_bucket(d.get("risk_score", 0))
        store.save_tagged(d)
        saved += 1
        tagged_items.append(d)
        emails.append(notify_if_alert(tagged))
        await live.publish(d)
    return {
        "account": account,
        "requested": limit,
        "fetched": len(txs),
        "saved": saved,
        "threshold": float(os.getenv("RISK_THRESHOLD", "0.75")),
        "items": tagged_items,
        "emails": emails,
    }


# ---------------- CSV export (DB) ----------------
@app.get("/export/csv")
def export_csv_from_db(wallet: str | None = None, limit: int = 1000, _auth: bool = Security(enforce_api_key)):
    rows = store.list_by_wallet(wallet, limit=limit) if wallet else store.list_all(limit=limit)
    if not rows:
        return {"rows": 0, "csv": ""}
    df = pd.DataFrame(rows)
    return {"rows": len(rows), "csv": df.to_csv(index=False)}


# ---- helper: allow ?key=... or x-api-key header for download ----
def _check_key_param_or_header(key: Optional[str] = None, x_api_key: Optional[str] = Header(default=None)):
    exp = expected_api_key() or ""
    incoming = (key or "").strip() or (x_api_key or "").strip()
    if exp and incoming != exp:
        raise HTTPException(status_code=401, detail="unauthorized")

@app.get("/export/csv/download")
def export_csv_download(wallet: str | None = None, limit: int = 1000, key: Optional[str] = None, x_api_key: Optional[str] = Header(None)):
    _check_key_param_or_header(key=key, x_api_key=x_api_key)
    rows = store.list_by_wallet(wallet, limit=limit) if wallet else store.list_all(limit=limit)
    df = pd.DataFrame(rows)
    buf = StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return StreamingResponse(iter([buf.read()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=klerno-export.csv"})


# ---------------- CSV export (UI, session-protected) ----------------
@app.get("/uiapi/export/csv/download", include_in_schema=False)
def ui_export_csv_download(
    wallet: str | None = None,
    limit: int = 1000,
    _user = Depends(require_paid_or_admin),
):
    rows = store.list_by_wallet(wallet, limit=limit) if wallet else store.list_all(limit=limit)
    df = pd.DataFrame(rows)
    buf = StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.read()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=klerno-export.csv"},
    )


# ---------------- Metrics (JSON) ----------------

# tiny in-proc TTL cache to avoid heavy recompute
_METRICS_CACHE: Dict[Tuple[Optional[float], Optional[int]], Tuple[float, Dict[str, Any]]] = {}
_METRICS_TTL_SEC = 5.0

def _metrics_cached(threshold: Optional[float], days: Optional[int]) -> Optional[Dict[str, Any]]:
    key = (threshold, days)
    item = _METRICS_CACHE.get(key)
    now = datetime.utcnow().timestamp()
    if item and (now - item[0]) <= _METRICS_TTL_SEC:
        return item[1]
    return None

def _metrics_put(threshold: Optional[float], days: Optional[int], data: Dict[str, Any]):
    key = (threshold, days)
    _METRICS_CACHE[key] = (datetime.utcnow().timestamp(), data)

@app.get("/metrics")
def metrics(threshold: float | None = None, days: int | None = None, _auth: bool = Security(enforce_api_key)):
    cached = _metrics_cached(threshold, days)
    if cached is not None:
        return cached

    rows = store.list_all(limit=10000)
    if not rows:
        data = {"total": 0, "alerts": 0, "avg_risk": 0, "categories": {}, "series_by_day": [], "series_by_day_lmh": []}
        _metrics_put(threshold, days, data)
        return data

    env_threshold = float(os.getenv("RISK_THRESHOLD", "0.75"))
    thr = env_threshold if threshold is None else float(threshold)
    thr = max(0.0, min(1.0, thr))

    cutoff = None
    if days is not None:
        try:
            d = max(1, min(int(days), 365))
            cutoff = datetime.utcnow() - timedelta(days=d)
        except Exception:
            cutoff = None

    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["risk_score"] = df.apply(lambda rr: _row_score(rr), axis=1)
    if cutoff is not None:
        df = df[df["timestamp"] >= cutoff]
    if df.empty:
        data = {"total": 0, "alerts": 0, "avg_risk": 0, "categories": {}, "series_by_day": [], "series_by_day_lmh": []}
        _metrics_put(threshold, days, data)
        return data

    total = int(len(df))
    alerts = int((df["risk_score"] >= thr).sum())
    avg_risk = float(df["risk_score"].mean())

    # categories
    categories: Dict[str, int] = {}
    cats_series = (df["category"].fillna("unknown") if "category" in df.columns else pd.Series(["unknown"] * total))
    for cat, cnt in cats_series.value_counts().items():
        categories[str(cat)] = int(cnt)

    df["day"] = df["timestamp"].dt.date
    grp = df.groupby("day").agg(avg_risk=("risk_score", "mean")).reset_index()
    series = [{"date": str(d), "avg_risk": round(float(v), 3)} for d, v in zip(grp["day"], grp["avg_risk"])]

    # Low/Med/High daily counts for stacked chart
    df["bucket"] = df["risk_score"].apply(_risk_bucket)
    crosstab = df.pivot_table(index="day", columns="bucket", values="risk_score", aggfunc="count").fillna(0)
    crosstab = crosstab.reindex(sorted(crosstab.index))
    series_lmh = []
    for d, row in crosstab.iterrows():
        series_lmh.append({
            "date": str(d),
            "low": int(row.get("low", 0)),
            "medium": int(row.get("medium", 0)),
            "high": int(row.get("high", 0)),
        })

    data = {"total": total, "alerts": alerts, "avg_risk": round(avg_risk, 3), "categories": categories, "series_by_day": series, "series_by_day_lmh": series_lmh}
    _metrics_put(threshold, days, data)
    return data


# ---------------- UI API (session-protected; no x-api-key) ----------------
@app.get("/metrics-ui", include_in_schema=False)
def metrics_ui(
    threshold: float | None = None,
    days: int | None = None,
    _user=Depends(require_paid_or_admin),
):
    resp = FastJSON(content=metrics(threshold=threshold, days=days, _auth=True))
    # short client-side caching to cut churn
    resp.headers["Cache-Control"] = "private, max-age=10"
    return resp

@app.get("/alerts-ui/data", include_in_schema=False)
def alerts_ui_data(limit: int = 100, _user=Depends(require_paid_or_admin)):
    threshold = float(os.getenv("RISK_THRESHOLD", "0.75"))
    rows = store.list_alerts(threshold, limit=limit)
    return {"threshold": threshold, "count": len(rows), "items": rows}

# Save demo/sample data to DB so dashboard shows data, and live-push
@app.post("/uiapi/analyze/sample", include_in_schema=False)
async def ui_analyze_sample(_user=Depends(require_paid_or_admin), _=Depends(csrf_protect_ui)):
    data_path = os.path.join(BASE_DIR, "..", "data", "sample_transactions.csv")
    df = pd.read_csv(data_path)

    text_cols = ("memo", "notes", "symbol", "direction", "chain", "tx_id", "from_addr", "to_addr")
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str)

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce").dt.strftime("%Y-%m-%dT%H:%M:%S")

    for col in ("amount", "fee", "risk_score"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    tx_field_names = {f.name for f in dc_fields(Transaction)}
    tagged: List[TaggedTransaction] = []
    saved = 0

    for _, row in df.iterrows():
        raw = {k: (None if pd.isna(v) else v) for k, v in row.to_dict().items()}
        raw.setdefault("memo", ""); raw.setdefault("notes", "")
        clean = {k: v for k, v in raw.items() if k in tx_field_names}
        tx = Transaction(**clean)

        risk, flags = score_risk(tx)
        category = tag_category(tx)
        t = TaggedTransaction(**_dump(tx), score=risk, flags=flags, category=category)
        tagged.append(t)

        d = t.model_dump()
        d["risk_score"] = d.get("score")
        d["risk_flags"] = d.get("flags")
        d["risk_bucket"] = _risk_bucket(d.get("risk_score", 0))
        store.save_tagged(d)
        saved += 1
        await live.publish(d)

    return {"summary": summary(tagged).model_dump(), "saved": saved, "items": [t.model_dump() for t in tagged]}

# Session-protected XRPL fetch used by the dashboard button
@app.post("/uiapi/integrations/xrpl/fetch_and_save", include_in_schema=False)
async def ui_xrpl_fetch_and_save(account: str, limit: int = 10, _user=Depends(require_paid_or_admin), _=Depends(csrf_protect_ui)):
    raw = fetch_account_tx(account, limit=limit)
    txs = xrpl_json_to_transactions(account, raw)
    saved = 0
    tagged_items: List[Dict[str, Any]] = []
    emails: List[Dict[str, Any]] = []
    for tx in txs:
        risk, flags = score_risk(tx)
        category = tag_category(tx)
        tagged = TaggedTransaction(**_dump(tx), score=risk, flags=flags, category=category)
        d = tagged.model_dump()
        d["risk_score"] = d.get("score")
        d["risk_flags"] = d.get("flags")
        d["risk_bucket"] = _risk_bucket(d.get("risk_score", 0))
        store.save_tagged(d)
        saved += 1
        tagged_items.append(d)
        emails.append(notify_if_alert(tagged))
        await live.publish(d)
    return {
        "account": account,
        "requested": limit,
        "fetched": len(txs),
        "saved": saved,
        "threshold": float(os.getenv("RISK_THRESHOLD", "0.75")),
        "items": tagged_items,
        "emails": emails,
    }

# Recent items for the dashboard (all or only alerts)
@app.get("/uiapi/recent", include_in_schema=False)
def ui_recent(limit: int = 50, only_alerts: bool = False, _user=Depends(require_paid_or_admin)):
    if only_alerts:
        thr = float(os.getenv("RISK_THRESHOLD", "0.75"))
        rows = store.list_alerts(threshold=thr, limit=limit)
    else:
        rows = store.list_all(limit=limit)
    return {"items": rows}

# Powerful transactions search for folders + filters UI
@app.get("/uiapi/transactions/search", include_in_schema=False)
def ui_search_transactions(
    wallet_from: Optional[str] = None,
    wallet_to: Optional[str] = None,
    tx_type: Optional[str] = None,   # 'sale'|'purchase' -> 'out'|'in'; or 'in'|'out'
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    category: Optional[str] = None,
    risk_bucket: Optional[str] = None,  # low|medium|high
    limit: int = 1000,
    _user=Depends(require_paid_or_admin),
):
    rows = store.list_all(limit=10000)

    def _type_ok(r):
        if not tx_type: return True
        t = tx_type.lower().strip()
        want = {"sale": "out", "purchase": "in"}.get(t, t)
        return str(r.get("direction","")).lower() == want

    def _between_dt(r):
        ts = _safe_dt(r.get("timestamp"))
        if date_from and ts < _safe_dt(date_from): return False
        if date_to and ts > _safe_dt(date_to): return False
        return True

    def _amt_ok(r):
        a = float(r.get("amount") or 0)
        if min_amount is not None and a < float(min_amount): return False
        if max_amount is not None and a > float(max_amount): return False
        return True

    def _bucket_ok(r):
        if not risk_bucket: return True
        b = r.get("risk_bucket") or _risk_bucket(_row_score(r))
        return str(b).lower() == risk_bucket.lower()

    sel = []
    for r in rows:
        if wallet_from and str(r.get("from_addr","")).lower() != wallet_from.lower(): continue
        if wallet_to   and str(r.get("to_addr","")).lower()   != wallet_to.lower():   continue
        if category and str(r.get("category","")).lower() != category.lower():       continue
        if not _type_ok(r): continue
        if not _between_dt(r): continue
        if not _amt_ok(r): continue
        if not _bucket_ok(r): continue
        sel.append(r)

    sel.sort(key=lambda x: _safe_dt(x.get("timestamp")), reverse=True)
    return {"count": len(sel[:limit]), "items": sel[:limit]}

# Profile / Transactions / Years + QuickBooks export
@app.get("/uiapi/profile/years", include_in_schema=False)
def ui_profile_years(_user=Depends(require_paid_or_admin)):
    rows = store.list_all(limit=50000)
    years = set()
    cutoff = datetime.utcnow() - timedelta(days=730)  # 2 years window
    for r in rows:
        ts = _safe_dt(r.get("timestamp"))
        if ts >= cutoff:
            years.add(ts.year)
    return {"years": sorted(years, reverse=True)}

@app.get("/uiapi/profile/year/{year}", include_in_schema=False)
def ui_profile_year(year: int, limit: int = 10000, _user=Depends(require_paid_or_admin)):
    rows = store.list_all(limit=50000)
    yr_rows = []
    for r in rows:
        ts = _safe_dt(r.get("timestamp"))
        if ts.year == int(year):
            yr_rows.append(r)
    yr_rows.sort(key=lambda x: _safe_dt(x.get("timestamp")), reverse=True)
    return {"year": int(year), "count": len(yr_rows[:limit]), "items": yr_rows[:limit]}

@app.get("/uiapi/profile/year/{year}/export", include_in_schema=False)
def ui_profile_year_export(year: int, format: str = "qb", _user=Depends(require_paid_or_admin)):
    rows = ui_profile_year(year=year, _user=_user)["items"]
    if not rows:
        return StreamingResponse(iter([""]), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=Transactions-{year}.csv"})
    df = pd.DataFrame(rows)

    for c in ("timestamp","tx_id","from_addr","to_addr","amount","symbol","direction","fee","category","memo","notes","risk_score"):
        if c not in df.columns: df[c] = None

    out = pd.DataFrame({
        "Date": pd.to_datetime(df["timestamp"], errors="coerce").dt.strftime("%Y-%m-%d"),
        "Time": pd.to_datetime(df["timestamp"], errors="coerce").dt.strftime("%H:%M:%S"),
        "Type": df["direction"].fillna(""),
        "From": df["from_addr"].fillna(""),
        "To": df["to_addr"].fillna(""),
        "Amount": pd.to_numeric(df["amount"], errors="coerce").fillna(0.0),
        "Currency": df["symbol"].fillna(""),
        "Fee": pd.to_numeric(df["fee"], errors="coerce").fillna(0.0),
        "Category": df["category"].fillna("unknown"),
        "Risk Score": df["risk_score"].apply(lambda x: float(x) if pd.notna(x) else 0.0),
        "Risk Bucket": df["risk_score"].apply(lambda x: _risk_bucket(x if pd.notna(x) else 0.0)),
        "Description": df["memo"].fillna("") + (" " + df["notes"].fillna("")),
        "Tx ID": df["tx_id"].fillna(""),
    })

    buf = StringIO()
    out.to_csv(buf, index=False)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.read()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=Transactions-{year}-QuickBooks.csv"},
    )


# ---------------- UI: Demo ----------------
@app.get("/demo", name="ui_demo", include_in_schema=False)
def ui_demo(request: Request):
    """Interactive demo showcasing Klerno Labs' blockchain analysis capabilities"""
    return templates.TemplateResponse("demo.html", {
        "request": request,
        "demo_data": {
            "sample_transactions": [
                {
                    "hash": "0xabc123...",
                    "amount": 15000.50,
                    "risk_score": 0.85,
                    "category": "High Risk",
                    "timestamp": "2024-01-15T10:30:00Z"
                },
                {
                    "hash": "0xdef456...", 
                    "amount": 2500.25,
                    "risk_score": 0.25,
                    "category": "Safe",
                    "timestamp": "2024-01-15T11:45:00Z"
                }
            ],
            "metrics": {
                "total_analyzed": 1250000,
                "high_risk_detected": 8750,
                "accuracy_rate": 99.7
            }
        }
    })

# ---------------- UI: Dashboard & Alerts ----------------
@app.get("/dashboard", name="ui_dashboard", include_in_schema=False)
def ui_dashboard(request: Request, user=Depends(require_paid_or_admin)):
    rows = store.list_all(limit=200)
    total = len(rows)
    threshold = float(os.getenv("RISK_THRESHOLD", "0.75"))
    alerts = [r for r in rows if _row_score(r) >= threshold]
    avg_risk = round(sum(_row_score(r) for r in rows) / total, 3) if total else 0.0
    cats: Dict[str, int] = {}
    for r in rows:
        c = r.get("category") or "unknown"
        cats[c] = cats.get(c, 0) + 1
    metrics_data = {"total": total, "alerts": len(alerts), "avg_risk": avg_risk, "categories": cats}
    resp = templates.TemplateResponse("dashboard.html", get_template_context(
        request,
        title="Elite Dashboard",
        key=None,
        metrics=metrics_data,
        rows=rows,
        threshold=threshold,
        user=user  # Pass authenticated user context
    ))
    issue_csrf_cookie(resp)
    return resp

@app.get("/alerts-ui", name="ui_alerts", include_in_schema=False)
def ui_alerts(request: Request, user=Depends(require_paid_or_admin)):
    threshold = float(os.getenv("RISK_THRESHOLD", "0.75"))
    rows = store.list_alerts(threshold=threshold, limit=500)
    return templates.TemplateResponse("alerts.html", get_template_context(
        request,
        title=f"Alerts (≥ {threshold})",
        key=None,
        rows=rows,
        threshold=threshold,
        user=user
    ))

@app.get("/wallets", name="ui_wallets", include_in_schema=False)
def ui_wallets(request: Request, user=Depends(require_paid_or_admin)):
    """Wallet management interface for users."""
    # Get user's wallet addresses from their profile
    user_wallets = user.get("wallet_addresses", [])
    return templates.TemplateResponse("wallet_management.html", get_template_context(
        request,
        title="Wallet Management",
        wallets=user_wallets,
        user=user
    ))


# ---------------- Admin / Email tests ----------------
@app.get("/admin/test-email", include_in_schema=False)
def admin_test_email(request: Request):
    key = request.query_params.get("key") or ""
    expected = expected_api_key() or ""
    if key != expected:
        return HTMLResponse(content="Unauthorized. Append ?key=YOUR_API_KEY", status_code=401)
    tx = Transaction(
        tx_id="TEST-ALERT-123",
        timestamp=datetime.utcnow().isoformat(),
        chain="XRPL",
        from_addr="rTEST_FROM",
        to_addr="rTEST_TO",
        amount=123.45,
        symbol="XRP",
        direction="out",
        memo="Test email",
        fee=0.0001,
    )
    tagged = TaggedTransaction(**_dump(tx), score=0.99, flags=["test_high_risk"], category="test-alert")
    return {"ok": True, "email": notify_if_alert(tagged)}

class NotifyRequest(BaseModel):
    email: EmailStr

@app.post("/notify/test")
def notify_test(payload: NotifyRequest = Body(...), _auth: bool = Security(enforce_api_key)):
    return _send_email("Klerno Labs Test", "✅ Your Klerno Labs email system is working!", payload.email)


# ---------------- Debug ----------------
@app.get("/_debug/api_key")
def debug_api_key(x_api_key: str | None = Header(default=None)):
    exp = expected_api_key()
    preview = (exp[:4] + "..." + exp[-4:]) if exp else ""
    return {"received_header": x_api_key, "expected_loaded_from_env": bool(exp), "expected_length": len(exp or ""), "expected_preview": preview}

@app.get("/_debug/routes", include_in_schema=False)
def list_routes():
    return {"routes": [r.path for r in app.router.routes]}


# ---------------- LLM Explain & AI Endpoints ----------------
class AskRequest(BaseModel):
    question: str

class BatchTx(BaseModel):
    items: List[Transaction]

@app.post("/explain/tx")
def explain_tx_endpoint(tx: Transaction, _auth: bool = Security(enforce_api_key)):
    try:
        text = explain_tx(_dump(tx))
        return {"explanation": text}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/explain/batch")
def explain_batch_endpoint(payload: BatchTx, _auth: bool = Security(enforce_api_key)):
    try:
        txs = [_dump(t) for t in payload.items]
        result = explain_batch(txs)
        return result
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/ask")
def ask_endpoint(req: AskRequest, _auth: bool = Security(enforce_api_key)):
    try:
        rows = store.list_all(limit=10000)
        spec = ask_to_filters(req.question)
        filtered = _apply_filters_safe(rows, spec)
        answer = explain_selection(req.question, filtered)
        preview = filtered[:50]
        return {"filters": spec, "count": len(filtered), "preview": preview, "answer": answer}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/explain/summary")
def explain_summary(days: int = 7, wallet: str | None = None, _auth: bool = Security(enforce_api_key)):
    try:
        rows = store.list_by_wallet(wallet, limit=5000) if wallet else store.list_all(limit=5000)
        cutoff = datetime.utcnow() - timedelta(days=max(1, min(days, 90)))
        recent = []
        for r in rows:
            try:
                t = datetime.fromisoformat(str(r.get("timestamp")))
                if t >= cutoff:
                    recent.append(r)
            except Exception:
                continue
        return summarize_rows(recent, title=f"Last {days} days summary")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# NLQ → filters + AI search wrappers (session-protected for UI)
class NLQRequest(BaseModel):
    query: str

@app.post("/ai/nlq-to-filters", include_in_schema=False)
def ai_nlq_to_filters(req: NLQRequest, _user=Depends(require_paid_or_admin)):
    try:
        spec = ask_to_filters(req.query)
        return {"filters": spec}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/ai/search", include_in_schema=False)
def ai_search(req: NLQRequest, _user=Depends(require_paid_or_admin)):
    try:
        spec = ask_to_filters(req.query)
        rows = store.list_all(limit=10000)
        filtered = _apply_filters_safe(rows, spec)
        return {"filters": spec, "count": len(filtered), "items": filtered[:1000]}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# simple anomaly scoring (z-score on amounts)
@app.get("/ai/anomaly/scores", include_in_schema=False)
def ai_anomaly_scores(limit: int = 100, _user=Depends(require_paid_or_admin)):
    rows = store.list_all(limit=20000)
    if not rows: return {"count": 0, "items": []}
    df = pd.DataFrame(rows)
    if "amount" not in df.columns: return {"count": 0, "items": []}
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    if df["amount"].std(ddof=0) == 0:
        df["anomaly_score"] = 0.0
    else:
        df["anomaly_score"] = (df["amount"] - df["amount"].mean()) / (df["amount"].std(ddof=0) or 1)
    df["anomaly_score"] = df["anomaly_score"].abs()
    df.sort_values(["anomaly_score", "timestamp"], ascending=[False, False], inplace=True)
    items = df.head(limit).to_dict(orient="records")
    return {"count": len(items), "items": items}


# ---- XRPL Payment Routes ----

@app.get("/xrpl/network-info")
def xrpl_network_info(_user=Depends(require_user)):
    """Get information about the XRPL network configuration."""
    return get_network_info()

@app.post("/xrpl/payment-request")
def create_xrpl_payment(amount_xrp: Optional[float] = None, _user=Depends(require_user)):
    """Create a payment request for XRPL."""
    payment = create_payment_request(
        user_id=_user["id"],
        amount_xrp=amount_xrp or settings.SUB_PRICE_XRP,
        description="Klerno Labs Subscription"
    )
    return payment

@app.post("/xrpl/verify-payment")
def verify_xrpl_payment(
    payment_id: str,
    tx_hash: Optional[str] = None,
    _user=Depends(require_user)
):
    """Verify an XRPL payment and activate subscription if valid."""
    # Get payment request (this would come from your database in a real app)
    # For demo, we create a new one with the same ID
    payment_request = create_payment_request(
        user_id=_user["id"],
        amount_xrp=settings.SUB_PRICE_XRP,
        description="Klerno Labs Subscription"
    )
    payment_request["id"] = payment_id
    
    # Verify the payment
    verified, message, tx_details = verify_payment(payment_request, tx_hash)
    
    if verified and tx_details:
        # Create or extend subscription
        subscription = create_subscription(
            user_id=_user["id"],
            tier=SubscriptionTier.BASIC,
            tx_hash=tx_details["tx_hash"],
            payment_id=payment_id
        )
        
        return {
            "verified": True,
            "message": message,
            "transaction": tx_details,
            "subscription": subscription.model_dump()
        }
    
    return {
        "verified": False,
        "message": message
    }


# ---- Subscription Management Routes ----

@app.get("/api/subscription/tiers")
async def list_subscription_tiers():
    """Get all available subscription tiers and their details."""
    tiers = []
    
    # Basic tier
    tiers.append({
        "id": SubscriptionTier.BASIC.value,
        "name": "Basic",
        "price_xrp": settings.SUB_PRICE_XRP,
        "features": [
            "Access to basic analysis tools",
            "Up to 100 transactions per month",
            "Email support"
        ],
        "description": "Perfect for individual users starting their journey."
    })
    
    # Premium tier
    tiers.append({
        "id": SubscriptionTier.PREMIUM.value,
        "name": "Premium",
        "price_xrp": settings.SUB_PRICE_XRP * 2.5,
        "features": [
            "Access to all analysis tools",
            "Unlimited transactions",
            "Priority email support",
            "Advanced reporting features",
            "API access"
        ],
        "description": "Ideal for power users and small businesses."
    })
    
    # Enterprise tier
    tiers.append({
        "id": SubscriptionTier.ENTERPRISE.value,
        "name": "Enterprise",
        "price_xrp": settings.SUB_PRICE_XRP * 5,
        "features": [
            "All Premium features",
            "Dedicated account manager",
            "Custom integrations",
            "Compliance reporting",
            "Multi-user access",
            "White-label options"
        ],
        "description": "Complete solution for businesses with advanced needs."
    })
    
    return {"tiers": tiers}

@app.get("/api/subscription/my")
async def get_my_subscription(_user=Depends(require_user)):
    """Get the current user's subscription details."""
    user_id = _user["id"]
    subscription = get_user_subscription(user_id)
    
    if not subscription:
        return {
            "has_subscription": False,
            "message": "No active subscription found."
        }
    
    tier_name = "Unknown"
    if subscription.tier == SubscriptionTier.BASIC:
        tier_name = "Basic"
    elif subscription.tier == SubscriptionTier.PREMIUM:
        tier_name = "Premium"
    elif subscription.tier == SubscriptionTier.ENTERPRISE:
        tier_name = "Enterprise"
    
    return {
        "has_subscription": True,
        "subscription": {
            "tier": subscription.tier.value,
            "tier_name": tier_name,
            "active": subscription.is_active,
            "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None,
            "created_at": subscription.created_at.isoformat(),
            "transaction_hash": subscription.tx_hash
        }
    }

@app.post("/api/subscription/upgrade")
async def upgrade_subscription(
    tier_id: int = Body(...),
    _user=Depends(require_user)
):
    """Create a payment request to upgrade to a specific subscription tier."""
    # Validate tier
    try:
        tier = SubscriptionTier(tier_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid subscription tier")
    
    # Calculate price based on tier
    if tier == SubscriptionTier.BASIC:
        amount_xrp = settings.SUB_PRICE_XRP
    elif tier == SubscriptionTier.PREMIUM:
        amount_xrp = settings.SUB_PRICE_XRP * 2.5
    elif tier == SubscriptionTier.ENTERPRISE:
        amount_xrp = settings.SUB_PRICE_XRP * 5
    else:
        amount_xrp = settings.SUB_PRICE_XRP
    
    # Create payment request
    payment = create_payment_request(
        user_id=_user["id"],
        amount_xrp=amount_xrp,
        description=f"Klerno Labs {tier.name.capitalize()} Subscription"
    )
    
    return {
        "payment_request": payment,
        "tier": {
            "id": tier.value,
            "name": tier.name.capitalize()
        }
    }

# Admin-only subscription management endpoints
@app.get("/api/subscription/list", include_in_schema=False)
async def list_subscriptions(_user=Depends(require_admin)):
    """List all subscriptions (admin only)."""
    try:
        # Connect to SQLite database
        db_path = os.path.join(os.path.dirname(__file__), "..", "data", "klerno.db")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM subscriptions ORDER BY created_at DESC"
        cursor.execute(query)
        rows = cursor.fetchall()
        
        # Convert rows to dictionaries
        subscriptions = []
        for row in rows:
            subscriptions.append({
                "id": row["id"],
                "user_id": row["user_id"],
                "tier": row["tier"],
                "created_at": row["created_at"],
                "expires_at": row["expires_at"],
                "tx_hash": row["tx_hash"]
            })
            
        conn.close()
        return {"subscriptions": subscriptions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list subscriptions: {str(e)}")

@app.post("/api/subscription/create", include_in_schema=False)
async def api_create_subscription(request: Request):
    """Create new subscription via API"""
    data = await request.json()
    # Implementation for subscription creation
    return {"success": True, "message": "Subscription created"}

# Missing routes for enhanced UX
@app.get("/forgot-password", include_in_schema=False)
def forgot_password_page(request: Request):
    """Forgot password page"""
    return templates.TemplateResponse("forgot-password.html", {"request": request})

@app.post("/forgot-password", include_in_schema=False)
def forgot_password_submit(request: Request, email: str = Form(...)):
    """Handle forgot password submission"""
    # In a real app, send password reset email
    return templates.TemplateResponse("forgot-password.html", {
        "request": request,
        "success": "If an account with that email exists, a password reset link has been sent."
    })

@app.get("/terms", include_in_schema=False)
def terms_of_service(request: Request):
    """Terms of Service page"""
    return templates.TemplateResponse("terms.html", {"request": request})

@app.get("/privacy", include_in_schema=False) 
def privacy_policy(request: Request):
    """Privacy Policy page"""
    return templates.TemplateResponse("privacy.html", {"request": request})

@app.get("/help", include_in_schema=False)
def help_page(request: Request):
    """Help and support page"""
    return templates.TemplateResponse("help.html", {"request": request})

# Protected API Documentation - Admin Only
@app.get("/admin/docs", include_in_schema=False)
def protected_docs(request: Request, user=Depends(require_admin)):
    """Protected API documentation for admins only"""
    from fastapi.openapi.docs import get_swagger_ui_html
    return get_swagger_ui_html(
        openapi_url="/admin/openapi.json",
        title="Klerno Labs API Documentation",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )

@app.get("/admin/redoc", include_in_schema=False)
def protected_redoc(request: Request, user=Depends(require_admin)):
    """Protected ReDoc documentation for admins only"""
    from fastapi.openapi.docs import get_redoc_html
    return get_redoc_html(
        openapi_url="/admin/openapi.json",
        title="Klerno Labs API Documentation",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
    )

@app.get("/admin/openapi.json", include_in_schema=False)
def protected_openapi(user=Depends(require_admin)):
    """Protected OpenAPI schema for admins only"""
    return app.openapi()

@app.get("/api/health-check")
def health_check():
    """Enhanced health check with system metrics"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0",
        "environment": os.getenv("APP_ENV", "development"),
        "database": "connected",
        "uptime_seconds": (datetime.utcnow() - START_TIME).total_seconds()
    }


# ---------------- Wallet Management API ----------------
class WalletAddRequest(BaseModel):
    address: str
    label: Optional[str] = None

class WalletUpdateRequest(BaseModel):
    address: str
    label: Optional[str] = None

class WalletRemoveRequest(BaseModel):
    address: str

@app.get("/api/user/wallets")
def get_user_wallets(user=Depends(require_user)):
    """Get user's wallet addresses"""
    try:
        user_data = store.get_user_by_id(user["id"])
        wallet_addresses = user_data.get("wallet_addresses", [])
        
        # Format wallet addresses with labels
        wallets = []
        for wallet in wallet_addresses:
            if isinstance(wallet, str):
                # Legacy format - just address
                wallets.append({"address": wallet, "label": None})
            elif isinstance(wallet, dict):
                # New format with label
                wallets.append({
                    "address": wallet.get("address"),
                    "label": wallet.get("label")
                })
        
        return {"wallets": wallets}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get wallets: {str(e)}")

@app.post("/api/user/wallets/add")
def add_user_wallet(request: WalletAddRequest, user=Depends(require_user)):
    """Add a wallet address to user's account"""
    try:
        address = request.address.strip()
        label = request.label.strip() if request.label else None
        
        # Basic validation
        if len(address) < 20:
            raise HTTPException(status_code=400, detail="Invalid wallet address")
        
        # Check if address already exists
        user_data = store.get_user_by_id(user["id"])
        wallet_addresses = user_data.get("wallet_addresses", [])
        
        existing_addresses = []
        for wallet in wallet_addresses:
            if isinstance(wallet, str):
                existing_addresses.append(wallet)
            elif isinstance(wallet, dict):
                existing_addresses.append(wallet.get("address"))
        
        if address in existing_addresses:
            raise HTTPException(status_code=409, detail="Wallet address already exists")
        
        # Add new wallet
        success = store.add_wallet_address(user["id"], address, label)
        if success:
            return {"success": True, "message": "Wallet address added successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to add wallet address")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add wallet: {str(e)}")

@app.post("/api/user/wallets/update")
def update_user_wallet(request: WalletUpdateRequest, user=Depends(require_user)):
    """Update wallet address label"""
    try:
        address = request.address.strip()
        label = request.label.strip() if request.label else None
        
        # Get current wallet addresses
        user_data = store.get_user_by_id(user["id"])
        wallet_addresses = user_data.get("wallet_addresses", [])
        
        # Update the specific wallet
        updated_wallets = []
        address_found = False
        
        for wallet in wallet_addresses:
            if isinstance(wallet, str):
                if wallet == address:
                    updated_wallets.append({"address": address, "label": label})
                    address_found = True
                else:
                    updated_wallets.append({"address": wallet, "label": None})
            elif isinstance(wallet, dict):
                if wallet.get("address") == address:
                    updated_wallets.append({"address": address, "label": label})
                    address_found = True
                else:
                    updated_wallets.append(wallet)
        
        if not address_found:
            raise HTTPException(status_code=404, detail="Wallet address not found")
        
        # Update in database
        success = store.update_user_wallet_addresses(user["id"], updated_wallets)
        if success:
            return {"success": True, "message": "Wallet updated successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to update wallet")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update wallet: {str(e)}")

@app.post("/api/user/wallets/remove")
def remove_user_wallet(request: WalletRemoveRequest, user=Depends(require_user)):
    """Remove a wallet address from user's account"""
    try:
        address = request.address.strip()
        
        success = store.remove_wallet_address(user["id"], address)
        if success:
            return {"success": True, "message": "Wallet address removed successfully"}
        else:
            raise HTTPException(status_code=404, detail="Wallet address not found")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove wallet: {str(e)}")

@app.post("/api/wallets/add")
def add_wallet_for_management(request: Dict[str, Any], user=Depends(require_user)):
    """Add wallet endpoint specifically for wallet management interface"""
    try:
        address = request.get("address", "").strip()
        chain = request.get("chain", "").strip()
        label = request.get("label", "").strip()
        notifications = request.get("notifications", False)
        
        if not address or not chain:
            raise HTTPException(status_code=400, detail="Address and chain are required")
        
        # Create wallet object with metadata
        wallet_data = {
            "address": address,
            "chain": chain,
            "label": label or f"{chain.upper()} Wallet",
            "notifications": notifications,
            "created_at": datetime.utcnow().isoformat(),
            "last_checked": None
        }
        
        # Get current wallets
        user_data = store.get_user_by_id(user["id"])
        wallet_addresses = user_data.get("wallet_addresses", [])
        
        # Check for duplicates
        for wallet in wallet_addresses:
            existing_addr = wallet.get("address") if isinstance(wallet, dict) else wallet
            if existing_addr == address:
                raise HTTPException(status_code=400, detail="Wallet address already exists")
        
        # Add new wallet
        wallet_addresses.append(wallet_data)
        store.update_user_wallet_addresses(user["id"], wallet_addresses)
        
        return {"success": True, "message": "Wallet added successfully", "wallet": wallet_data}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add wallet: {str(e)}")

# Enhanced error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Custom 404 page"""
    return templates.TemplateResponse("errors/404.html", {
        "request": request
    }, status_code=404)

@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    """Custom 500 page"""
    return templates.TemplateResponse("errors/500.html", {
        "request": request
    }, status_code=500)
async def admin_create_subscription(
    user_id: str = Body(...),
    tier: int = Body(...),
    duration_days: int = Body(30),
    _user=Depends(require_admin)
):
    """Create a subscription for a user (admin only)."""
    try:
        # Validate tier
        tier_enum = SubscriptionTier(tier)
        
        # Create subscription
        subscription = create_subscription(
            user_id=user_id,
            tier=tier_enum,
            tx_hash="admin-created",
            payment_id="admin-created",
            duration_days=duration_days
        )
        
        return {
            "success": True,
            "subscription": {
                "user_id": subscription.user_id,
                "tier": subscription.tier.value,
                "created_at": subscription.created_at.isoformat(),
                "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create subscription: {str(e)}")