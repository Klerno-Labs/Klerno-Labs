#!/usr/bin/env python3
"""Comprehensive security middleware for FastAPI applications."""

import logging
import time
from collections.abc import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add comprehensive security headers to all responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        response = await call_next(request)

        # Security headers
        security_headers = {
            # Prevent XSS attacks
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            # Content Security Policy
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "connect-src 'self'; "
                "font-src 'self'; "
                "object-src 'none'; "
                "media-src 'self'; "
                "frame-src 'none';"
            ),
            # HTTPS enforcement (in production)
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            # Referrer policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            # Permissions policy
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            # Server information hiding
            "Server": "FastAPI",
            # Cache control for sensitive endpoints
            "Cache-Control": "no-store, no-cache, must-revalidate, private",
            "Pragma": "no-cache",
            "Expires": "0",
        }

        # Apply security headers
        for header, value in security_headers.items():
            response.headers[header] = value

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests for security monitoring."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request details."""
        start_time = time.perf_counter()

        # Log request
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        logger.info(
            f"Request: {request.method} {request.url.path} "
            f"from {client_ip} [{user_agent}]",
        )

        response = await call_next(request)

        # Log response
        process_time = time.perf_counter() - start_time
        logger.info(
            f"Response: {response.status_code} processed in {process_time:.4f}s",
        )

        return response


def configure_security_middleware(app: FastAPI) -> None:
    """Configure all security middleware for the FastAPI app."""
    # Add compression middleware first
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Add CORS middleware with secure settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:8080",
        ],  # Configure for production
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
        max_age=600,  # Cache preflight responses
    )

    # Add security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)

    # Add request logging middleware
    app.add_middleware(RequestLoggingMiddleware)

    logger.info("Security middleware configured successfully")


# Example usage:
# from security_middleware import configure_security_middleware
# configure_security_middleware(app)
