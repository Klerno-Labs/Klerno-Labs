# app / security.py
from __future__ import annotations

import contextlib
import hmac
import os
import secrets
import time
from pathlib import Path
from typing import Any

from dotenv import find_dotenv, load_dotenv
from fastapi import Header, HTTPException, Request, status

# --- Load .env robustly (works from OneDrive, nested folders, etc.) ---
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOTENV_PATH = find_dotenv(usecwd=True) or str(PROJECT_ROOT / ".env")

# Deferred initialization flags
_env_loaded = False
_data_dir_ensured = False


def _ensure_env_loaded() -> None:
    """Load environment from DOTENV_PATH once (deferred to runtime)."""
    global _env_loaded
    if _env_loaded:
        return
    with contextlib.suppress(Exception):
        # best-effort; failure to load env is non-fatal here
        load_dotenv(dotenv_path=DOTENV_PATH, override=False)
    _env_loaded = True


# --- File-based key storage (used when ENV key is not set) ---

_DATA_DIR = PROJECT_ROOT / "data"
_KEY_FILE = _DATA_DIR / "api_key.secret"
_META_FILE = _DATA_DIR / "api_key.meta"


def _ensure_data_dir() -> None:
    """Create data directory on first write/read (best-effort)."""
    global _data_dir_ensured
    if _data_dir_ensured:
        return
    with contextlib.suppress(Exception):
        # ignore filesystem errors at import time; surface on write if needed
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _data_dir_ensured = True


def expected_api_key() -> str:
    """
    Priority:
      1) ENV: X_API_KEY (or API_KEY)
      2) File: data / api_key.secret (written by admin rotation)
    """
    # ensure env vars are loaded (deferred)
    _ensure_env_loaded()
    env = (os.getenv("X_API_KEY") or os.getenv("API_KEY") or "").strip()
    if env:
        return env
    if _KEY_FILE.exists():
        try:
            return _KEY_FILE.read_text(encoding="utf-8").strip()
        except Exception:
            return ""
    return ""


def _write_api_key(new_key: str) -> None:
    _ensure_data_dir()
    _KEY_FILE.write_text(new_key, encoding="utf-8")
    with contextlib.suppress(Exception):
        _KEY_FILE.chmod(0o600)  # best effort hardening
    _META_FILE.write_text(str(int(time.time())), encoding="utf-8")


def generate_api_key(nbytes: int = 32) -> str:
    """Create a url - safe API key (admin can rotate)."""
    return "sk-" + secrets.token_urlsafe(nbytes)


def api_key_last_updated() -> int | None:
    # ensure data dir exists
    _ensure_data_dir()
    if _META_FILE.exists():
        try:
            return int(_META_FILE.read_text(encoding="utf-8").strip())
        except Exception:
            return None
    return None


async def enforce_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None),
) -> bool:
    """
    Authorize EITHER:
      • x - api - key header that matches the expected key, OR
      • a valid session (so the web dashboard works without pasting a key)

    Dev - friendly: if no key is configured at all, allow requests.
    Enhanced with audit logging for security events.
    """
    from .audit_logger import AuditEventType, log_api_access, log_security_event

    exp = expected_api_key()

    # 0) Dev mode: if no key configured, allow.
    if not exp:
        log_api_access(str(request.url.path), request.method, None, False, request)
        return True

    # 1) Header path for external clients / integrations.
    if x_api_key and hmac.compare_digest(x_api_key.strip(), exp):
        log_api_access(str(request.url.path), request.method, None, True, request)
        return True

    # 2) Session fallback for browser dashboard (valid JWT cookie).
    try:
        # Dynamic import avoids circular-import issues and keeps static
        # checkers happy without broad ignores.
        import importlib

        deps_mod = importlib.import_module("app.deps")
        require_user = getattr(deps_mod, "require_user", None)
        if require_user is None:
            raise RuntimeError("require_user not available")

        # Call the dependency; some implementations accept Request, others do not.
        try:
            user = require_user(request)
        except TypeError:
            user = require_user()

        log_api_access(
            str(request.url.path),
            request.method,
            str(user.get("id")),
            False,
            request,
        )
        return True
    except Exception:
        # Fall through to API key denial below
        pass

    # 3) Log unauthorized access attempt and deny
    log_security_event(
        AuditEventType.API_ACCESS_DENIED,
        {
            "endpoint": str(request.url.path),
            "method": request.method,
            "has_api_key": bool(x_api_key),
            "reason": "invalid_credentials",
        },
        request,
    )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized: missing or invalid API key / session",
    )


def rotate_api_key() -> str:
    """Admin-only: generate and persist a new API key (file).

    Includes audit logging.
    """
    from .audit_logger import AuditEvent, AuditEventType, audit_logger

    old_key_preview = preview_api_key().get("preview", "none")
    key = generate_api_key()
    _write_api_key(key)

    # Log the key rotation for security auditing
    audit_logger.log_event(
        AuditEvent(
            event_type=AuditEventType.API_KEY_ROTATION,
            outcome="success",
            details={
                "old_key_preview": old_key_preview,
                "new_key_preview": (
                    key[:4] + "..." + key[-4:] if len(key) >= 8 else "***"
                ),
            },
        )
    )

    return key


def preview_api_key() -> dict[str, Any]:
    """Return masked preview + metadata (never the full key)."""
    key = expected_api_key()
    if not key:
        return {"configured": False}
    preview = (key[:4] + "..." + key[-4:]) if len(key) >= 8 else "***"
    return {
        "configured": True,
        "preview": preview,
        "updated_at": api_key_last_updated(),
        "source": (
            "env" if (os.getenv("X_API_KEY") or os.getenv("API_KEY")) else "file"
        ),
    }
