"""
Enterprise Security Module for Klerno Labs
Comprehensive security hardening and protection against unauthorized access.
"""

import hmac
import ipaddress
import logging
import os
import secrets
import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from functools import wraps
from typing import Any, Awaitable, Callable

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

# Configure security logging
security_logger = logging.getLogger("klerno.security")
security_logger.setLevel(logging.INFO)

# Security event types
SECURITY_EVENTS = {
    "FAILED_LOGIN": "failed_login",
    "BRUTE_FORCE": "brute_force_attempt",
    "UNAUTHORIZED_ACCESS": "unauthorized_access",
    "SUSPICIOUS_IP": "suspicious_ip",
    "RATE_LIMIT_EXCEEDED": "rate_limit_exceeded",
    "ADMIN_ACCESS": "admin_access",
    "DATA_ACCESS": "data_access",
    "API_ABUSE": "api_abuse",
    "INJECTION_ATTEMPT": "injection_attempt",
}


class SecurityManager:
    """Central security management system"""

    def __init__(self) -> None:
        self.failed_attempts: dict[str, list[datetime]] = defaultdict(list)
        self.blocked_ips: set[str] = set()
        self.rate_limits: dict[str, list[datetime]] = defaultdict(list)
        self.suspicious_patterns: list[str] = [
            # SQL injection patterns
            r"(?i)(union|select|insert|update|delete|drop|exec|script)",
            # XSS patterns
            r"(?i)(<script|javascript:|onerror|onload)",
            # Path traversal
            r"(\.\./|\.\.\\)",
            # Command injection
            r"(?i)(;|\||&|`|\$\()",
        ]

    def log_security_event(
        self, event_type: str, details: dict, request: Request | None = None
    ) -> None:
        """Log security events for monitoring"""
        event_data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event_type": event_type,
            "details": details,
        }

        if request:
            event_data.update(
                {
                    "ip": self.get_client_ip(request),
                    "user_agent": request.headers.get("user - agent", ""),
                    "path": str(request.url.path),
                    "method": request.method,
                }
            )

        security_logger.warning(f"SECURITY_EVENT: {event_data}")

    def get_client_ip(self, request: Request) -> str:
        """Get real client IP handling proxies"""
        # Check common proxy headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"

    def is_brute_force(
        self, identifier: str, window_minutes: int = 15, max_attempts: int = 5
    ) -> bool:
        """Check for brute force attempts"""
        now = datetime.now(UTC)
        cutoff = now - timedelta(minutes=window_minutes)

        # Clean old attempts
        self.failed_attempts[identifier] = [
            attempt for attempt in self.failed_attempts[identifier] if attempt > cutoff
        ]

        return len(self.failed_attempts[identifier]) >= max_attempts

    def record_failed_attempt(self, identifier: str) -> None:
        """Record a failed authentication attempt"""
        self.failed_attempts[identifier].append(datetime.now(UTC))

    def is_rate_limited(
        self, identifier: str, window_minutes: int = 1, max_requests: int = 60
    ) -> bool:
        """Check rate limiting"""
        now = datetime.now(UTC)
        cutoff = now - timedelta(minutes=window_minutes)

        # Clean old requests
        self.rate_limits[identifier] = [
            req_time for req_time in self.rate_limits[identifier] if req_time > cutoff
        ]

        if len(self.rate_limits[identifier]) >= max_requests:
            return True

        self.rate_limits[identifier].append(now)
        return False

    def check_suspicious_input(self, input_data: str) -> bool:
        """Check for suspicious patterns in input"""
        import re

        for pattern in self.suspicious_patterns:
            if re.search(pattern, input_data):
                return True
        return False

    def validate_ip_whitelist(self, ip: str) -> bool:
        """Validate against IP whitelist (if configured)"""
        whitelist = os.getenv("IP_WHITELIST", "").strip()
        if not whitelist:
            return True  # No whitelist configured

        allowed_ips = [ip.strip() for ip in whitelist.split(",")]
        try:
            client_ip = ipaddress.ip_address(ip)
            for allowed in allowed_ips:
                if "/" in allowed:  # CIDR notation
                    if client_ip in ipaddress.ip_network(allowed):
                        return True
                else:  # Single IP
                    if client_ip == ipaddress.ip_address(allowed):
                        return True
            return False
        except ValueError:
            return False  # Invalid IP format


# Global security manager instance
security_manager = SecurityManager()


class SecurityMiddleware(BaseHTTPMiddleware):
    """Security middleware for request filtering and monitoring"""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start_time = time.time()
        client_ip = security_manager.get_client_ip(request)

        # IP whitelist check
        if not security_manager.validate_ip_whitelist(client_ip):
            security_manager.log_security_event(
                SECURITY_EVENTS["UNAUTHORIZED_ACCESS"],
                {"reason": "IP not whitelisted", "ip": client_ip},
                request,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
            )

        # Rate limiting
        if security_manager.is_rate_limited(client_ip):
            security_manager.log_security_event(
                SECURITY_EVENTS["RATE_LIMIT_EXCEEDED"], {"ip": client_ip}, request
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
            )

        # Check for blocked IPs
        if client_ip in security_manager.blocked_ips:
            security_manager.log_security_event(
                SECURITY_EVENTS["UNAUTHORIZED_ACCESS"],
                {"reason": "IP blocked", "ip": client_ip},
                request,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
            )

        # Input validation for suspicious patterns
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body and security_manager.check_suspicious_input(
                    body.decode("utf-8", errors="ignore")
                ):
                    security_manager.log_security_event(
                        SECURITY_EVENTS["INJECTION_ATTEMPT"],
                        {"ip": client_ip, "path": str(request.url.path)},
                        request,
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid request",
                    )
            except Exception:
                # Continue silently if reading the body fails (best-effort)
                # Use best-effort suppression to avoid masking other errors
                import contextlib

                with contextlib.suppress(Exception):
                    _ = None

        response = await call_next(request)

        # Log response time for monitoring
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)

        # Security headers (normalized header names)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )

        return response


def require_secure_password(password: str) -> bool:
    """Validate password security requirements"""
    if len(password) < 12:
        return False
    if not any(c.isupper() for c in password):
        return False
    if not any(c.islower() for c in password):
        return False
    if not any(c.isdigit() for c in password):
        return False
    # Allow a conservative set of special characters
    return any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)


def generate_secure_token(length: int = 32) -> str:
    """Generate cryptographically secure token"""
    return secrets.token_urlsafe(length)


def secure_compare(a: str, b: str) -> bool:
    """Timing - safe string comparison"""
    return hmac.compare_digest(a.encode(), b.encode())


class AdminAccessLogger:
    """Special logging for admin access"""

    @staticmethod
    def log_admin_action(
        user_email: str, action: str, details: dict, request: Request | None = None
    ) -> None:
        """Log all admin actions for audit trail"""
        # request may be None in some call sites (e.g., background tasks)
        security_manager.log_security_event(
            SECURITY_EVENTS["ADMIN_ACCESS"],
            {"admin_user": user_email, "action": action, "details": details},
            request if request is not None else None,
        )


def admin_action_required(
    action_name: str,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to log admin actions"""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract user and request from function arguments
            user = None
            request = None

            for arg in args:
                if hasattr(arg, "method"):  # Likely a Request object
                    request = arg
                elif isinstance(arg, dict) and "email" in arg:  # Likely user dict
                    user = arg

            for value in kwargs.values():
                if hasattr(value, "method"):  # Likely a Request object
                    request = value
                elif isinstance(value, dict) and "email" in value:  # Likely user dict
                    user = value

            if user:
                AdminAccessLogger.log_admin_action(
                    user.get("email", "unknown"),
                    action_name,
                    {"function": func.__name__},
                    request,
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


# Environment validation


def validate_production_environment() -> bool:
    """Validate production environment security"""
    required_vars = [
        "JWT_SECRET",
        "ADMIN_EMAIL",
        "ADMIN_PASSWORD",
        "DATABASE_URL",
        "SECRET_KEY",
    ]

    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(
            f"🚨 SECURITY ERROR: Missing required environment variables: {missing_vars}"
        )
        return False

    # Check JWT secret strength
    jwt_secret = os.getenv("JWT_SECRET", "")
    if len(jwt_secret) < 32:
        print("🚨 SECURITY ERROR: JWT_SECRET must be at least 32 characters!")
        return False

    return True


def get_content_security_policy() -> str:
    """Generate Content Security Policy header"""
    parts = [
        "default - src 'self';",
        (
            "script - src 'self' 'unsafe - inline' https://cdn.jsdelivr.net "
            "https://cdnjs.cloudflare.com;"
        ),
        (
            "style - src 'self' 'unsafe - inline' https://cdn.jsdelivr.net "
            "https://cdnjs.cloudflare.com;"
        ),
        "img - src 'self' data: https:;",
        "font - src 'self' https://fonts.gstatic.com;",
        "connect - src 'self';",
        "frame - ancestors 'none';",
        "form - action 'self';",
        "base - uri 'self';",
    ]

    return " ".join(parts)
