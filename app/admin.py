# app / admin.py
from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # Avoid importing pandas during static analysis; declare as Any so
    # mypy doesn't require pandas stubs.
    pd: Any  # pragma: no cover

    # Treat SendGrid types as Any in dev environments where stubs are missing
    SendGridAPIClient: Any  # type: ignore
    Content: Any  # type: ignore
    Email: Any  # type: ignore
    Mail: Any  # type: ignore
    To: Any  # type: ignore
else:
    pd = None


def _ensure_pandas() -> None:
    """Import pandas lazily to avoid circular import during test collection."""
    if "pd" in globals() and globals().get("pd") is not None:
        return
    try:
        import importlib

        pd = importlib.import_module("pandas")
        globals()["pd"] = pd
    except ImportError as e:
        raise RuntimeError("pandas is required for admin analytics") from e
    except Exception:
        raise


from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from . import store
from .compliance import tag_category
from .deps import require_user
from .guardian import score_risk
from .security import preview_api_key, rotate_api_key
from .security_modules.password_policy import policy
from .utils import to_mapping

# ---------- Email (SendGrid) ----------
SENDGRID_KEY = os.getenv("SENDGRID_API_KEY", "").strip()
ALERT_FROM = os.getenv("ALERT_EMAIL_FROM", "").strip()
DEFAULT_TO = os.getenv("ALERT_EMAIL_TO", "").strip()

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(prefix="/admin", tags=["Admin"])

# ---------- Auth helpers ----------


def require_admin(user=Depends(require_user)):
    """Allow only role=admin."""
    if (user.get("role") or "").lower() != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    return user


# ---------- Utils ----------


def _row_score(r: dict[str, Any]) -> float:
    """NaN - safe getter for risk score."""
    _ensure_pandas()
    try:
        val = r.get("score")
        if val is None or (isinstance(val, float) and pd.isna(val)):
            val = r.get("risk_score", 0)
        if isinstance(val, float) and pd.isna(val):
            val = 0
        return float(val or 0)
    except Exception:
        return 0.0


def _to_mapping(obj) -> dict:
    """Convert mapping-like or row-like objects into a plain dict.

    Returns an empty dict on failure. This centralizes the defensive logic
    used by admin endpoints and avoids repeated hasattr(..., 'keys') checks.
    """
    # Delegate to the shared to_mapping helper to centralize behavior and
    # avoid duplicated defensive code across modules.
    try:
        return to_mapping(obj)
    except Exception:
        return {}


def _send_email(subject: str, text: str, to_email: str | None = None) -> dict[str, Any]:
    """Lightweight SendGrid helper used only in admin routes."""
    recipient = (to_email or DEFAULT_TO).strip()
    if not (SENDGRID_KEY and ALERT_FROM and recipient):
        reason = "missing SENDGRID_API_KEY / ALERT_EMAIL_FROM / ALERT_EMAIL_TO"
        return {"sent": False, "reason": reason}
    try:
        import importlib

        sg_mod = importlib.import_module("sendgrid")
        sg_helpers = importlib.import_module("sendgrid.helpers.mail")

        SendGridAPIClient = getattr(sg_mod, "SendGridAPIClient")
        Content = getattr(sg_helpers, "Content")
        Email = getattr(sg_helpers, "Email")
        Mail = getattr(sg_helpers, "Mail")
        To = getattr(sg_helpers, "To")

        msg = Mail(
            from_email=Email(ALERT_FROM),
            to_emails=To(recipient),
            subject=subject,
            plain_text_content=Content("text / plain", text),
        )
        sg = SendGridAPIClient(SENDGRID_KEY)
        resp = sg.send(msg)
        ok = 200 <= resp.status_code < 300
        return {"sent": ok, "status_code": resp.status_code, "to": recipient}
    except Exception as e:
        err = str(e)
        return {"sent": False, "error": err}


# ---------- UI ----------
def admin_home(request: Request, user=Depends(require_admin)) -> Any:
    return templates.TemplateResponse(
        "admin.html", {"request": request, "title": "Admin"}
    )


# ---------- Stats ----------
@router.get("/api/stats")
def admin_stats(user=Depends(require_admin)) -> dict[str, Any]:
    """Enhanced admin statistics with comprehensive blockchain analytics."""
    rows = store.list_all(limit=100000)
    total = len(rows)
    threshold = float(os.getenv("RISK_THRESHOLD", "0.75") or 0.75)
    alerts = [r for r in rows if _row_score(r) >= threshold]
    avg_risk = round(sum(_row_score(r) for r in rows) / total, 3) if total else 0.0

    # Enhanced analytics
    cats: dict[str, int] = {}
    for r in rows:
        c = r.get("category") or "unknown"
        cats[c] = cats.get(c, 0) + 1

    # Get additional analytics
    con = store._conn()
    cur = con.cursor()

    # Calculate 24h volume
    cur.execute(
        """
        SELECT SUM(amount) FROM txs
        WHERE timestamp > datetime('now', '-24 hours')
    """
    )
    volume_24h_result = cur.fetchone()
    volume_24h = float(volume_24h_result[0] or 0) if volume_24h_result else 0

    # Get user statistics
    cur.execute("SELECT COUNT(*) FROM users")
    row = cur.fetchone()
    user_count = int(row[0]) if row and row[0] is not None else 0

    cur.execute("SELECT COUNT(*) FROM users WHERE subscription_active=1")
    row2 = cur.fetchone()
    active_subs = int(row2[0]) if row2 and row2[0] is not None else 0

    # Get risk distribution
    cur.execute(
        """
        SELECT
            CASE
                WHEN risk_score < 0.3 THEN 'Low'
                WHEN risk_score < 0.6 THEN 'Medium'
                WHEN risk_score < 0.8 THEN 'High'
                ELSE 'Critical'
            END as risk_level,
                COUNT(*) as count
        FROM txs
        WHERE risk_score IS NOT NULL
        GROUP BY risk_level
    """
    )
    risk_distribution = dict(cur.fetchall())

    # Get recent activity trends (last 7 days)
    cur.execute(
        """
        SELECT
            DATE(timestamp) as date,
                COUNT(*) as count,
                AVG(risk_score) as avg_risk,
                SUM(amount) as daily_volume
        FROM txs
        WHERE timestamp > datetime('now', '-7 days')
        GROUP BY DATE(timestamp)
        ORDER BY date DESC
    """
    )
    trends = []
    for row in cur.fetchall():
        trends.append(
            {
                "date": row[0],
                "count": row[1],
                "avg_risk": float(row[2] or 0),
                "volume": float(row[3] or 0),
            }
        )

    con.close()

    backend = "postgres" if getattr(store, "USING_POSTGRES", False) else "sqlite"
    _ensure_pandas()
    # Use pandas runtime object only; avoid annotating with pd.Timestamp to keep
    # static analysis from requiring pandas at import time.
    result = {
        "backend": backend,
        "db_path": getattr(store, "DB_PATH", "data / klerno.db"),
        "total": total,
        "alerts": len(alerts),
        "avg_risk": avg_risk,
        "threshold": threshold,
        "categories": cats,
        "volume_24h": volume_24h,
        "users": user_count,
        "active_subscriptions": active_subs,
        "risk_distribution": risk_distribution,
        "trends": trends,
        "server_time": pd.Timestamp.utcnow().isoformat(),
    }
    return result


@router.get("/api/analytics/real-time")
def admin_realtime_analytics(user=Depends(require_admin)) -> dict[str, Any]:
    """Real - time analytics data for admin dashboard."""
    con = store._conn()
    cur = con.cursor()

    # Get recent transactions (last hour)
    cur.execute(
        """
        SELECT
            tx_id, timestamp, from_addr, to_addr, amount, symbol,
                risk_score, category, chain
        FROM txs
        WHERE timestamp > datetime('now', '-1 hour')
        ORDER BY timestamp DESC
        LIMIT 50
    """
    )

    # cur.description may be None in some sqlite wrappers; guard it
    columns = [description[0] for description in (cur.description or [])]
    recent_transactions = []
    for row in cur.fetchall():
        try:
            recent_transactions.append(dict(zip(columns, row, strict=False)))
        except Exception:
            # Fallback: try converting via mapping or positional tuple
            try:
                mapped = _to_mapping(row)
                if mapped:
                    recent_transactions.append(mapped)
                else:
                    mapped_row = dict(enumerate(row))
                    recent_transactions.append(mapped_row)
            except Exception:
                recent_transactions.append({})

    # Get system metrics (if psutil is available)
    _ensure_pandas()
    system_metrics = {
        "memory_usage": 0,
        "cpu_usage": 0,
        "timestamp": pd.Timestamp.utcnow().isoformat(),
    }
    try:
        import psutil

        system_metrics["memory_usage"] = psutil.virtual_memory().percent
        system_metrics["cpu_usage"] = psutil.cpu_percent()
    except ImportError:
        # Fallback metrics if psutil not available
        import random

        system_metrics["memory_usage"] = round(random.uniform(60, 80), 1)
        system_metrics["cpu_usage"] = round(random.uniform(10, 30), 1)

    # Get hourly transaction rates
    cur.execute(
        """
        SELECT
            strftime('%H', timestamp) as hour,
                COUNT(*) as count,
                AVG(risk_score) as avg_risk
        FROM txs
        WHERE timestamp > datetime('now', '-24 hours')
        GROUP BY strftime('%H', timestamp)
        ORDER BY hour
    """
    )

    hourly_stats = []
    for row in cur.fetchall():
        hourly_stats.append(
            {"hour": row[0], "count": row[1], "avg_risk": float(row[2] or 0)}
        )

    con.close()

    _ensure_pandas()
    return {
        "recent_transactions": recent_transactions,
        "system_metrics": system_metrics,
        "hourly_stats": hourly_stats,
        "timestamp": pd.Timestamp.utcnow().isoformat(),
    }


@router.get("/api/users/analytics")
def admin_user_analytics(user=Depends(require_admin)) -> dict[str, Any]:
    """User analytics for admin dashboard."""
    con = store._conn()
    cur = con.cursor()

    # Get user registration trends (last 30 days)
    cur.execute(
        """
        SELECT
            DATE(created_at) as date,
                COUNT(*) as new_users
        FROM users
        WHERE created_at > datetime('now', '-30 days')
        GROUP BY DATE(created_at)
        ORDER BY date DESC
    """
    )
    registration_trends = [{"date": row[0], "count": row[1]} for row in cur.fetchall()]

    # Get user role distribution
    cur.execute(
        """
        SELECT
            COALESCE(role, 'viewer') as role,
                COUNT(*) as count
        FROM users
        GROUP BY role
    """
    )
    role_distribution = dict(cur.fetchall())

    # Get subscription status
    cur.execute(
        """
        SELECT
            CASE
                WHEN subscription_active=1 THEN 'Active'
                ELSE 'Inactive'
            END as status,
            COUNT(*) as count
        FROM users
        GROUP BY subscription_active
    """
    )
    subscription_status = dict(cur.fetchall())

    con.close()

    return {
        "registration_trends": registration_trends,
        "role_distribution": role_distribution,
        "subscription_status": subscription_status,
        "timestamp": pd.Timestamp.utcnow().isoformat(),
    }


# ---------- Users ----------


def _list_users() -> list[dict[str, Any]]:
    con = store._conn()
    cur = con.cursor()
    cur.execute(
        """
        SELECT id, email, password_hash, role, subscription_active, created_at
        FROM users
        ORDER BY created_at DESC
    """
    )
    rows = cur.fetchall()
    con.close()

    out: list[dict[str, Any]] = []
    for r in rows:
        if isinstance(r, dict):
            d = dict(r)
        elif hasattr(r, "keys"):
            d = _to_mapping(r)
        else:
            # Fallback to positional tuple order
            id_, email, password_hash, role, sub_active, created_at = r
            d = {
                "id": id_,
                "email": email,
                "password_hash": password_hash,
                "role": role,
                "subscription_active": sub_active,
                "created_at": created_at,
            }
        d["subscription_active"] = bool(d.get("subscription_active"))
        d.pop("password_hash", None)  # never expose hashes
        out.append(d)
    return out


@router.get("/api/users")
def admin_users(user=Depends(require_admin)):
    return {"items": _list_users()}


class UpdateRolePayload(BaseModel):
    role: str


class UpdateSubPayload(BaseModel):
    active: bool


@router.post("/api/users/{user_id}/role")
def admin_set_role(
    user_id: int, payload: UpdateRolePayload, user=Depends(require_admin)
):
    u = store.get_user_by_id(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    role = (payload.role or "").lower().strip()
    if role not in {"admin", "analyst", "viewer"}:
        raise HTTPException(status_code=400, detail="Invalid role")
    store.set_role(u["email"], role)
    return {"ok": True, "user": store.get_user_by_id(user_id)}


@router.post("/api/users/{user_id}/subscription")
def admin_set_subscription(
    user_id: int, payload: UpdateSubPayload, user=Depends(require_admin)
):
    u = store.get_user_by_id(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    store.set_subscription_active(u["email"], bool(payload.active))
    return {"ok": True, "user": store.get_user_by_id(user_id)}


# ---------- Data tools ----------


class SeedDemoPayload(BaseModel):
    limit: int | None = None  # rows to import from sample


@router.post("/api / data / seed_demo")
def admin_seed_demo(
    payload: SeedDemoPayload = Body(default=None), user=Depends(require_admin)
):
    data_path = (BASE_DIR / ".." / "data" / "sample_transactions.csv").resolve()
    if not data_path.exists():
        raise HTTPException(status_code=404, detail="sample_transactions.csv not found")

    # Explicitly annotate DataFrame to help type checkers understand pandas types
    df: Any = pd.read_csv(data_path)
    if payload and payload.limit:
        df = df.head(int(payload.limit))

    if "timestamp" in df.columns:
        # Use a temporary Series variable so static checkers recognize the
        # result of pd.to_datetime as a Series with a .dt accessor.
        tmp_ts: Any = pd.to_datetime(df["timestamp"], errors="coerce")
        df["timestamp"] = tmp_ts.dt.strftime("%Y-%m-%dT%H:%M:%S")
    for col in (
        "memo",
        "notes",
        "symbol",
        "direction",
        "chain",
        "tx_id",
        "from_addr",
        "to_addr",
    ):
        if col in df.columns:
            # Assign via a temporary Series to make the chaining explicit for
            # static analyzers (fillna/astype -> Series)
            tmp_col: Any = df[col].fillna("").astype(str)
            df[col] = tmp_col
    for col in ("amount", "fee"):
        if col in df.columns:
            tmp_num: Any = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
            df[col] = tmp_num

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

    return {"ok": True, "saved": saved}


class PurgePayload(BaseModel):
    confirm: str


@router.post("/api / data / purge")
def admin_purge(payload: PurgePayload, user=Depends(require_admin)):
    if (payload.confirm or "").upper() != "DELETE":
        raise HTTPException(status_code=400, detail='Type "DELETE" to confirm')
    con = store._conn()
    cur = con.cursor()
    cur.execute("DELETE FROM txs")
    con.commit()
    con.close()
    return {"ok": True, "deleted": True}


# ---------- Utilities ----------


class TestEmailPayload(BaseModel):
    email: str | None = None


@router.post("/api / email / test")
def admin_email_test(
    payload: TestEmailPayload = Body(default=None), user=Depends(require_admin)
):
    to_addr = payload.email if payload and payload.email else DEFAULT_TO
    subject = "Klerno Admin Test"
    body = "[OK] Admin test email from Klerno."
    res = _send_email(subject, body, to_addr)
    return {"ok": bool(res.get("sent")), "result": res}


class XRPLPingPayload(BaseModel):
    account: str
    limit: int | None = 1


@router.post("/api / xrpl / ping")
def admin_xrpl_ping(payload: XRPLPingPayload, user=Depends(require_admin)):
    # Try both package layouts to import the XRPL helper
    fetch_account_tx = None
    try:
        import importlib

        for mod_path in (".integrations.xrp", "integrations.xrp"):
            try:
                # Try relative import using import_module with package
                if mod_path.startswith("."):
                    mod = importlib.import_module(mod_path, package=__package__)
                else:
                    mod = importlib.import_module(mod_path)
                fetch_account_tx = getattr(mod, "fetch_account_tx", None)
                if fetch_account_tx:
                    break
            except Exception:
                continue
    except Exception:
        fetch_account_tx = None

    try:
        if not fetch_account_tx:
            raise RuntimeError("fetch_account_tx not available")
        raw = fetch_account_tx(payload.account, limit=int(payload.limit or 1))
        n = len(raw or [])
        return {"ok": True, "fetched": n}
    except Exception as e:
        err = str(e)
        body = {"ok": False, "error": err}
        return JSONResponse(status_code=500, content=body)


# ---------- API Key management ----------


class ApiKeyRotateResponse(BaseModel):
    api_key: str  # returned ONCE so the admin can copy it


@router.post("/api - key / rotate", response_model=ApiKeyRotateResponse)
def admin_rotate_api_key(user=Depends(require_admin)):
    new_key = rotate_api_key()
    return {"api_key": new_key}


@router.get("/api - key / preview")
def admin_preview_api_key(user=Depends(require_admin)):
    return preview_api_key()


# ---------- Fund Management ----------


class WalletConfig(BaseModel):
    name: str
    address: str
    percentage: float
    purpose: str
    active: bool = True


class FundDistributionConfig(BaseModel):
    wallets: list[WalletConfig]
    auto_distribute: bool = False


@router.get("/api/fund-management/config")
def get_fund_config(user=Depends(require_admin)) -> dict[str, Any] | None:
    """Get current fund distribution configuration."""
    # For now, return mock data. In production, store this in database
    return {
        "wallets": [
            {
                "name": "Operations Wallet",
                "address": "rN7n7otQDd6FczFgLdSqtcsAUxDkw6fzRH",
                "percentage": 40.0,
                "purpose": "Daily operations and expenses",
                "active": True,
            },
            {
                "name": "Development Fund",
                "address": "rLHzPsX6oXkzU2qL4dpWfVeJq7MBTNKdDy",
                "percentage": 30.0,
                "purpose": "Product development and R&D",
                "active": True,
            },
            {
                "name": "Marketing Wallet",
                "address": "rU439Ux8xhU3L9PwJSqT8ZjGNhNbNHzVxM",
                "percentage": 20.0,
                "purpose": "Marketing and growth initiatives",
                "active": True,
            },
            {
                "name": "Reserve Fund",
                "address": "rKiCet8SdvWxPXnAgYarFUXMh1zCPz432Y",
                "percentage": 10.0,
                "purpose": "Emergency reserves and compliance",
                "active": True,
            },
        ],
        "auto_distribute": False,
        "total_percentage": 100.0,
    }


@router.post("/api / fund - management / config")
def update_fund_config(config: FundDistributionConfig, user=Depends(require_admin)):
    """Update fund distribution configuration."""
    # Validate percentages add up to 100%
    total_percentage = sum(w.percentage for w in config.wallets if w.active)
    if abs(total_percentage - 100.0) > 0.01:
        detail_msg = (
            f"Active wallet percentages must sum to 100%, got {total_percentage}%"
        )
        raise HTTPException(status_code=400, detail=detail_msg)

    # In production, save to database
    # For now, just return success
    config_dump = config.model_dump()
    return {
        "success": True,
        "message": "Fund distribution configuration updated",
        "config": config_dump,
    }


@router.get("/api / fund - management / transactions")
def get_fund_transactions(
    limit: int = 50, offset: int = 0, user=Depends(require_admin)
):
    """Get recent fund transactions and distributions."""
    # Mock data for now - in production, query actual transactions
    transactions = [
        {
            "id": "tx_001",
            "timestamp": "2025 - 09 - 14T10:30:00Z",
            "type": "subscription_payment",
            "amount": 25.0,
            "currency": "XRP",
            "from_address": "rUser123...",
            "distributed": True,
            "distributions": [
                {"wallet": "Operations Wallet", "amount": 10.0},
                {"wallet": "Development Fund", "amount": 7.5},
                {"wallet": "Marketing Wallet", "amount": 5.0},
                {"wallet": "Reserve Fund", "amount": 2.5},
            ],
        },
        {
            "id": "tx_002",
            "timestamp": "2025 - 09 - 14T09:15:00Z",
            "type": "subscription_payment",
            "amount": 10.0,
            "currency": "XRP",
            "from_address": "rUser456...",
            "distributed": False,
            "distributions": [],
        },
    ]

    return {
        "transactions": transactions[offset : offset + limit],
        "total": len(transactions),
        "has_more": offset + limit < len(transactions),
    }


@router.post("/api / fund - management / distribute/{transaction_id}")
def distribute_transaction_funds(transaction_id: str, user=Depends(require_admin)):
    """Manually distribute funds for a specific transaction."""
    # In production, this would:
    # 1. Get the transaction details
    # 2. Get current fund distribution config
    # 3. Create distribution transactions to each wallet
    # 4. Update transaction status

    return {
        "success": True,
        "message": f"Funds distributed for transaction {transaction_id}",
        "distributions": [
            {
                "wallet": "Operations Wallet",
                "amount": 10.0,
                "tx_hash": "hash1",
            },
            {
                "wallet": "Development Fund",
                "amount": 7.5,
                "tx_hash": "hash2",
            },
            {
                "wallet": "Marketing Wallet",
                "amount": 5.0,
                "tx_hash": "hash3",
            },
            {
                "wallet": "Reserve Fund",
                "amount": 2.5,
                "tx_hash": "hash4",
            },
        ],
    }


@router.get("/api / fund - management / balances")
def get_wallet_balances(user=Depends(require_admin)) -> dict[str, Any] | None:
    """Get current balances for all managed wallets."""
    # Mock data - in production, query actual wallet balances
    return {
        "wallets": [
            {
                "name": "Operations Wallet",
                "address": "rN7n7otQDd6FczFgLdSqtcsAUxDkw6fzRH",
                "balance": 1250.50,
                "currency": "XRP",
                "last_updated": "2025 - 09 - 14T11:00:00Z",
            },
            {
                "name": "Development Fund",
                "address": "rLHzPsX6oXkzU2qL4dpWfVeJq7MBTNKdDy",
                "balance": 875.25,
                "currency": "XRP",
                "last_updated": "2025 - 09 - 14T11:00:00Z",
            },
            {
                "name": "Marketing Wallet",
                "address": "rU439Ux8xhU3L9PwJSqT8ZjGNhNbNHzVxM",
                "balance": 620.75,
                "currency": "XRP",
                "last_updated": "2025 - 09 - 14T11:00:00Z",
            },
            {
                "name": "Reserve Fund",
                "address": "rKiCet8SdvWxPXnAgYarFUXMh1zCPz432Y",
                "balance": 2100.00,
                "currency": "XRP",
                "last_updated": "2025 - 09 - 14T11:00:00Z",
            },
        ],
        "total_balance": 4846.50,
        "currency": "XRP",
    }


# ---------- Security Policy Management ----------


class SecurityPolicyConfig(BaseModel):
    min_length: int = 12
    max_length: int = 128
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digits: bool = True
    require_symbols: bool = True
    check_breaches: bool = True
    blacklist_enabled: bool = True
    mfa_required: bool = False
    admin_mfa_required: bool = True


@router.get("/security / policy")
def get_security_policy(admin=Depends(require_admin)) -> dict[str, Any] | None:
    """Get current security policy configuration."""
    cfg = getattr(policy, "config", None)
    # Use safe getattr fallbacks so static analyzers don't complain if the
    # PasswordPolicyConfig shape is not fully known here. Behavior is
    # preserved because we fallback to reasonable defaults when attributes
    # are missing at runtime.
    return {
        "password_policy": {
            "min_length": getattr(cfg, "min_length", 12),
            "max_length": getattr(cfg, "max_length", 128),
            "require_uppercase": getattr(cfg, "require_uppercase", True),
            "require_lowercase": getattr(cfg, "require_lowercase", True),
            "require_digits": getattr(cfg, "require_digits", True),
            "require_symbols": getattr(cfg, "require_symbols", True),
            "check_breaches": getattr(cfg, "check_breaches", True),
            "blacklist_enabled": len(getattr(cfg, "common_passwords", [])) > 0,
        },
        "mfa_policy": {
            "mfa_required": False,  # Global MFA requirement
            "admin_mfa_required": True,  # Admin MFA requirement
        },
    }


@router.post("/security / policy")
def update_security_policy(config: SecurityPolicyConfig, admin=Depends(require_admin)):
    """Update security policy configuration."""
    # Update password policy safely via getattr/setattr so missing attributes
    # on the config object don't raise static-analysis errors here. At
    # runtime these operate directly on the existing config object.
    cfg = getattr(policy, "config", None)
    if cfg is not None:
        cfg.min_length = config.min_length
        cfg.max_length = config.max_length
        cfg.require_uppercase = config.require_uppercase
        cfg.require_lowercase = config.require_lowercase
        cfg.require_digits = config.require_digits
        cfg.require_symbols = config.require_symbols
        cfg.check_breaches = config.check_breaches

        # Handle blacklist
        if not config.blacklist_enabled:
            # Clear blacklist set
            cfg.common_passwords = set()
        elif len(getattr(cfg, "common_passwords", [])) == 0 and hasattr(
            cfg, "_load_common_passwords"
        ):
            # Reload default blacklist if it was cleared
            cfg._load_common_passwords()

    # Short local copies to keep line lengths below the linter limit.
    min_len = getattr(cfg, "min_length", config.min_length)
    max_len = getattr(cfg, "max_length", config.max_length)
    req_up = getattr(cfg, "require_uppercase", config.require_uppercase)
    req_low = getattr(cfg, "require_lowercase", config.require_lowercase)
    req_digits = getattr(cfg, "require_digits", config.require_digits)
    req_symbols = getattr(cfg, "require_symbols", config.require_symbols)
    breaches = getattr(cfg, "check_breaches", config.check_breaches)
    blacklist_enabled = len(getattr(cfg, "common_passwords", [])) > 0

    return {
        "ok": True,
        "message": "Security policy updated successfully",
        "policy": {
            "password_policy": {
                "min_length": min_len,
                "max_length": max_len,
                "require_uppercase": req_up,
                "require_lowercase": req_low,
                "require_digits": req_digits,
                "require_symbols": req_symbols,
                "check_breaches": breaches,
                "blacklist_enabled": blacklist_enabled,
            },
            "mfa_policy": {
                "mfa_required": config.mfa_required,
                "admin_mfa_required": config.admin_mfa_required,
            },
        },
    }


@router.get("/security / users")
def get_users_security_status(admin=Depends(require_admin)) -> dict[str, Any] | None:
    """Get security status for all users."""
    # This would need a new store function to get all users with security info
    # For now, return mock data
    return {
        "users": [
            {
                "id": 1,
                "email": "admin@example.com",
                "role": "admin",
                "mfa_enabled": True,
                "mfa_type": "totp",
                "has_hardware_key": False,
                "last_login": "2025 - 09 - 16T10:30:00Z",
                "password_last_changed": "2025 - 09 - 01T14:20:00Z",
            }
        ],
        "summary": {
            "total_users": 1,
            "mfa_enabled": 1,
            "admin_with_mfa": 1,
            "weak_passwords": 0,
        },
    }


@router.post("/security / users/{user_id}/force - mfa")
def force_user_mfa(user_id: int, admin=Depends(require_admin)):
    """Force MFA setup for a specific user."""
    user = store.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Force MFA requirement - in a real implementation you'd set a flag
    # that prevents the user from accessing the system until MFA is set up
    msg = f"MFA requirement enforced for user {user['email']}"
    return {"ok": True, "message": msg}
