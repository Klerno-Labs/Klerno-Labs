# app / security_middleware.py
"""
Enhanced security middleware for TLS enforcement and security headers.
"""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse, Response


class TLSEnforcementMiddleware(BaseHTTPMiddleware):
    """
    Enforces HTTPS in production environments by redirecting HTTP to HTTPS.
    """

    def __init__(self, app, enforce_tls: bool | None = None):
        super().__init__(app)
        # Default to enforcing TLS in production
        if enforce_tls is None:
            app_env = os.getenv("APP_ENV", "dev").lower()
            self.enforce_tls = app_env in ("production", "prod", "staging")
        else:
            self.enforce_tls = enforce_tls

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Skip TLS enforcement for health checks and development
        if not self.enforce_tls or request.url.path in ["/health", "/healthz"]:
            return await call_next(request)

        # Check if request is already HTTPS
        is_secure = self._is_secure_request(request)

        if not is_secure and request.method == "GET":
            # Redirect HTTP GET requests to HTTPS
            secure_url = request.url.replace(scheme="https")
            return RedirectResponse(url=str(secure_url), status_code=301)
        elif not is_secure:
            # For non - GET requests, return 400 Bad Request
            return Response(
                content="HTTPS required",
                status_code=400,
                headers={"Content - Type": "text / plain"},
            )

        return await call_next(request)

    def _is_secure_request(self, request: Request) -> bool:
        """Check if request is over HTTPS, accounting for proxy headers."""
        # Direct HTTPS
        if request.url.scheme == "https":
            return True

        # Behind proxy / load balancer
        forwarded_proto = request.headers.get("x-forwarded-proto", "").lower()
        if forwarded_proto == "https":
            return True

        # Cloudflare
        cf_visitor = request.headers.get("cf - visitor", "").lower()
        return "https" in cf_visitor


class EnhancedSecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Enhanced security headers middleware with production - grade configurations.
    """

    def __init__(self, app):
        super().__init__(app)
        self.app_env = os.getenv("APP_ENV", "dev").lower()
        self.is_production = self.app_env in ("production", "prod")

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)

        # Enhanced Content Security Policy
        csp_directives = [
            "default - src 'self'",
            "script - src 'self' 'unsafe - inline' https://cdn.jsdelivr.net https://js.stripe.com",
            "style - src 'self' 'unsafe - inline' https://cdn.jsdelivr.net",
            "img - src 'self' data: https:",
            "font - src 'self' data: https://cdn.jsdelivr.net",
            "connect - src 'self' ws: wss: https://api.stripe.com",
            "frame - src https://js.stripe.com https://hooks.stripe.com",
            "object - src 'none'",
            "base - uri 'self'",
            "frame - ancestors 'none'",
            "form - action 'self'",
            "upgrade - insecure - requests" if self.is_production else "",
        ]
        csp = "; ".join(filter(None, csp_directives))

        # Security headers
        security_headers = {
            "Content-Security-Policy": csp,
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X - XSS - Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions - Policy": (
                "camera=(), microphone=(), geolocation=(), "
                "payment=(), usb=(), magnetometer=(), gyroscope=()"
            ),
            "Cross - Origin - Embedder - Policy": "require - corp",
            "Cross - Origin - Opener - Policy": "same - origin",
            "Cross - Origin - Resource - Policy": "same - origin",
        }

        # HSTS for HTTPS requests
        if self._is_secure_request(request):
            if self.is_production:
                # Production: long max - age with preload
                security_headers["Strict-Transport-Security"] = (
                    "max - age=31536000; includeSubDomains; preload"
                )
            else:
                # Staging: shorter max - age, no preload
                security_headers["Strict-Transport-Security"] = (
                    "max - age=86400; includeSubDomains"
                )

        # Apply headers that aren't already set
        for header, value in security_headers.items():
            if header not in response.headers:
                response.headers[header] = value

        return response

    def _is_secure_request(self, request: Request) -> bool:
        """Check if request is over HTTPS."""
        return (
            request.url.scheme == "https"
            or request.headers.get("x-forwarded-proto", "").lower() == "https"
        )
