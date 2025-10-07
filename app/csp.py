"""Content Security Policy (CSP) nonce utilities and middleware.

Enables a report-only CSP with per-request nonce if CSP_NONCE_ENABLED=true.
Environment variables:
- CSP_NONCE_ENABLED=true         Enable nonce injection & header updates
- CSP_REPORT_ONLY=true           Use Report-Only header (default true)
- CSP_BASE_POLICY=...            Base policy without script/style-src (we append nonce)

A minimal violation report endpoint can be wired to receive JSON reports at
`/csp/report` when enabled.
"""

from __future__ import annotations

import base64
import os
import secrets
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastapi import Request

NONCE_ATTRIBUTE = "csp_nonce"


def generate_nonce(size: int = 16) -> str:
    # URL-safe base64 without padding for CSP usage
    raw = secrets.token_bytes(size)
    return base64.b64encode(raw).decode("ascii").rstrip("=")


def csp_enabled() -> bool:
    return os.getenv("CSP_NONCE_ENABLED", "false").lower() in {"1", "true", "yes"}


def report_only() -> bool:
    return os.getenv("CSP_REPORT_ONLY", "true").lower() in {"1", "true", "yes"}


def base_policy() -> str:
    return os.getenv("CSP_BASE_POLICY", "default-src 'self'")


def add_csp_middleware(app) -> None:
    if not csp_enabled():
        return

    @app.middleware("http")
    async def _add_csp(request: Request, call_next: Callable[[Request], Any]) -> Any:
        nonce = generate_nonce()
        # Stash nonce on request state so templates / other middleware can use it
        setattr(request.state, NONCE_ATTRIBUTE, nonce)
        response = await call_next(request)
        bp = base_policy()
        # Append script-src/style-src with nonce fallback to self
        script = f"script-src 'self' 'nonce-{nonce}'"
        style = f"style-src 'self' 'nonce-{nonce}'"
        # Add optional report-uri for report collection endpoint
        report_uri = "/csp/report"
        policy = (
            f"{bp}; {script}; {style}; report-uri {report_uri}"
            if bp
            else f"{script}; {style}; report-uri {report_uri}"
        )
        header_name = (
            "Content-Security-Policy-Report-Only"
            if report_only()
            else "Content-Security-Policy"
        )
        response.headers[header_name] = policy
        return response
