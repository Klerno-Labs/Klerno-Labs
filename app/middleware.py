"""
Middleware for request / response logging, metrics, and monitoring.
"""

import time
import uuid
from collections.abc import Callable
from typing import Any

import structlog
from fastapi import Request, Response
from prometheus_client import Counter, Gauge, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import PlainTextResponse

from app.logging_config import log_request_response

logger = structlog.get_logger("middleware")


# Prometheus metrics
REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status_code"]
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint", "status_code"],
)

ACTIVE_REQUESTS = Gauge("http_requests_active", "Active HTTP requests")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Start timer
        start_time = time.time()

        # Log request start
        logger.debug(
            "Request started",
            method=request.method,
            url=str(request.url),
            user_agent=request.headers.get("user-agent"),
            request_id=request_id,
        )

        # Process request
        try:
            response = await call_next(request)
        except Exception as exc:
            # Log exception
            duration = time.time() - start_time
            logger.error(
                "Request failed with exception",
                method=request.method,
                url=str(request.url),
                duration=duration,
                exception=str(exc),
                request_id=request_id,
            )
            raise

        # Calculate duration
        duration = time.time() - start_time

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        # Log request completion
        user_id = getattr(request.state, "user_id", None)

        log_request_response(
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            duration=duration,
            request_id=request_id,
            user_id=user_id,
        )

        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting Prometheus metrics."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip metrics collection for the metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)

        # Increment active requests
        ACTIVE_REQUESTS.inc()

        # Start timer
        start_time = time.time()

        try:
            response = await call_next(request)
        except Exception:
            # Still record metrics for failed requests
            duration = time.time() - start_time
            endpoint = self._get_endpoint_path(request)

            REQUEST_COUNT.labels(
                method=request.method, endpoint=endpoint, status_code=500
            ).inc()

            REQUEST_DURATION.labels(
                method=request.method, endpoint=endpoint, status_code=500
            ).observe(duration)

            ACTIVE_REQUESTS.dec()
            raise

        # Calculate duration
        duration = time.time() - start_time
        endpoint = self._get_endpoint_path(request)

        # Record metrics
        REQUEST_COUNT.labels(
            method=request.method, endpoint=endpoint, status_code=response.status_code
        ).inc()

        REQUEST_DURATION.labels(
            method=request.method, endpoint=endpoint, status_code=response.status_code
        ).observe(duration)

        # Decrement active requests
        ACTIVE_REQUESTS.dec()

        return response

    def _get_endpoint_path(self, request: Request) -> str:
        """Extract endpoint path for metrics, normalizing dynamic segments."""
        path = request.url.path

        # Normalize common dynamic path patterns
        # Replace UUIDs with placeholder
        import re

        path = re.sub(
            r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "/{id}",
            path,
        )

        # Replace numeric IDs
        path = re.sub(r"/\d+", "/{id}", path)

        # Replace wallet addresses (common pattern: rXXX...)
        path = re.sub(r"/r[a-zA-Z0-9]{25,}", "/{wallet}", path)

        return path


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Add security headers
        response.headers.update(
            {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "X-XSS-Protection": "1; mode=block",
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                "Content-Security-Policy": (
                    "default-src 'self'; "
                    "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                    "style-src 'self' 'unsafe-inline'; "
                    "img-src 'self' data: https:; "
                    "font-src 'self' https:; "
                    "connect-src 'self' https:; "
                    "frame-ancestors 'none';"
                ),
                "Referrer-Policy": "strict-origin-when-cross-origin",
                "Permissions-Policy": (
                    "geolocation=(), "
                    "microphone=(), "
                    "camera=(), "
                    "payment=(), "
                    "usb=(), "
                    "magnetometer=(), "
                    "gyroscope=(), "
                    "speaker=()"
                ),
            }
        )

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting middleware."""

    def __init__(self, app, requests_per_minute: int = 60) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests: dict[str, list[float]] = {}  # ip -> list[Any] of timestamps

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/healthz", "/metrics"]:
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        current_time = time.time()

        # Clean old requests
        self._clean_old_requests(current_time)

        # Check rate limit
        if self._is_rate_limited(client_ip, current_time):
            logger.warning(
                "Rate limit exceeded",
                client_ip=client_ip,
                path=request.url.path,
                method=request.method,
            )

            from app.exceptions import RateLimitException

            raise RateLimitException(retry_after=60)

        # Record request
        self._record_request(client_ip, current_time)

        return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address."""
        # Check for forwarded headers (behind proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fallback to direct connection
        return request.client.host if request.client else "unknown"

    def _clean_old_requests(self, current_time: float) -> None:
        """Remove requests older than 1 minute."""
        cutoff_time = current_time - 60  # 1 minute ago

        for ip in list[Any](self.requests):
            self.requests[ip] = [
                timestamp for timestamp in self.requests[ip] if timestamp > cutoff_time
            ]

            # Remove empty entries
            if not self.requests[ip]:
                del self.requests[ip]

    def _is_rate_limited(self, ip: str, current_time: float) -> bool:
        """Check if IP is rate limited."""
        if ip not in self.requests:
            return False

        return len(self.requests[ip]) >= self.requests_per_minute

    def _record_request(self, ip: str, current_time: float) -> None:
        """Record a request for the IP."""
        if ip not in self.requests:
            self.requests[ip] = []

        self.requests[ip].append(current_time)


def metrics_endpoint() -> PlainTextResponse:
    """Prometheus metrics endpoint."""
    return PlainTextResponse(
        generate_latest(), media_type="text/plain; version=0.0.4; charset=utf-8"
    )
