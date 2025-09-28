"""
Unified Security Module for Klerno Labs

This module consolidates all security functionality into a single source of truth:
- API key authentication
- Rate limiting & DDoS protection
- Security middleware
- Audit logging
- Threat detection
- Input validation & sanitization
- Security headers

Replaces: security.py, enterprise_security.py, enterprise_security_enhanced.py,
         advanced_security.py, advanced_security_hardening.py, security_hardening_advanced.py
"""

from __future__ import annotations

import hmac
import logging
import os
import secrets
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, cast

from dotenv import find_dotenv, load_dotenv
from fastapi import Header, HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# Configure unified security logging
security_logger = logging.getLogger("klerno.security.unified")
security_logger.setLevel(logging.INFO)

# Project root for configuration
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOTENV_PATH = find_dotenv(usecwd=True) or str(PROJECT_ROOT / ".env")
load_dotenv(dotenv_path=DOTENV_PATH, override=False)

# Data directory for secure storage
_DATA_DIR = PROJECT_ROOT / "data"
_DATA_DIR.mkdir(parents=True, exist_ok=True)
_KEY_FILE = _DATA_DIR / "api_key.secret"
_META_FILE = _DATA_DIR / "api_key.meta"

# Security configuration (build in steps for clearer typing)
_rate_limit_requests = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
_rate_limit_window = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
_max_request_size = int(os.getenv("MAX_REQUEST_SIZE", "10485760"))  # 10MB

# Compute blocked and trusted IPs in a type-safe way
_blocked_ips_raw = os.getenv("BLOCKED_IPS")
if _blocked_ips_raw:
    _blocked_ips_set: set[str] = set(_blocked_ips_raw.split(","))
else:
    _blocked_ips_set = set()

_trusted_ips_raw = os.getenv("TRUSTED_IPS", "127.0.0.1,::1") or ""
_trusted_ips_set: set[str] = (
    set(_trusted_ips_raw.split(",")) if _trusted_ips_raw else set()
)

SECURITY_CONFIG = {
    "rate_limit_requests": _rate_limit_requests,
    "rate_limit_window": _rate_limit_window,
    "max_request_size": _max_request_size,
    "blocked_ips": _blocked_ips_set,
    "trusted_ips": _trusted_ips_set,
    "require_secure_headers": os.getenv("REQUIRE_SECURE_HEADERS", "true").lower()
    == "true",
}

# In-memory security storage (fallback if Redis unavailable)
_rate_limits: dict[str, list[float]] = defaultdict(list)
_security_events: list[dict[str, Any]] = []
_blocked_ips: set[str] = cast(set[str], SECURITY_CONFIG.get("blocked_ips", set()))
_suspicious_activity: dict[str, int] = defaultdict(int)


# Security event types
class SecurityEventType:
    FAILED_LOGIN = "failed_login"
    BRUTE_FORCE = "brute_force_attempt"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    SUSPICIOUS_IP = "suspicious_ip"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    ADMIN_ACCESS = "admin_access"
    DATA_ACCESS = "data_access"
    SUSPICIOUS_REQUEST = "suspicious_request"
    INJECTION_ATTEMPT = "injection_attempt"
    XSS_ATTEMPT = "xss_attempt"


# Audit event types for system logging
class AuditEventType:
    SYSTEM_START = "system.start"
    SYSTEM_SHUTDOWN = "system.shutdown"
    LOGIN = "auth.login"
    LOGOUT = "auth.logout"
    SETTINGS_CHANGED = "settings.changed"
    ERROR = "system.error"
    DATA_ACCESS = "data.access"
    ADMIN_ACTION = "admin.action"


# Audit event data structure
class AuditEvent:
    def __init__(
        self,
        event_type: str,
        outcome: str = "success",
        details: dict[str, Any] | None = None,
        user_id: str | None = None,
    ):
        self.event_type = event_type
        self.outcome = outcome
        self.details = details or {}
        self.user_id = user_id
        self.timestamp = datetime.now(UTC)


class SecurityManager:
    """Unified security manager handling all security operations."""

    def __init__(self) -> None:
        self.logger = security_logger
        self.config = SECURITY_CONFIG

    def log_security_event(
        self, event_type: str, details: dict[str, Any], ip: str | None = None
    ) -> None:
        """Log security events with standardized format."""
        event = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event_type": event_type,
            "ip_address": ip,
            "details": details,
        }
        _security_events.append(event)

        # Log to file
        self.logger.warning(f"Security Event: {event_type} from {ip} - {details}")

        # Auto-block suspicious IPs
        if ip and event_type in [
            SecurityEventType.BRUTE_FORCE,
            SecurityEventType.INJECTION_ATTEMPT,
        ]:
            _suspicious_activity[ip] += 1
            if _suspicious_activity[ip] >= 5:
                self.block_ip(
                    ip, f"Auto-blocked after {_suspicious_activity[ip]} security events"
                )

    def block_ip(self, ip: str, reason: str = "Security violation") -> None:
        """Block an IP address."""
        _blocked_ips.add(ip)
        self.log_security_event(
            SecurityEventType.SUSPICIOUS_IP, {"action": "blocked", "reason": reason}, ip
        )

    def is_ip_blocked(self, ip: str) -> bool:
        """Check if an IP is blocked."""
        return ip in _blocked_ips

    def is_rate_limited(self, identifier: str) -> bool:
        """Check and update rate limiting for an identifier."""
        now: float = time.time()
        # SECURITY_CONFIG is constructed from ints above; narrow types here so
        # mypy knows arithmetic and comparisons are valid.
        # config values may be typed as object; cast to Any so int() overloads match
        window: int = int(cast(Any, self.config.get("rate_limit_window", 60)))
        max_requests: int = int(cast(Any, self.config.get("rate_limit_requests", 100)))

        # Clean old entries
        _rate_limits[identifier] = [
            timestamp
            for timestamp in _rate_limits[identifier]
            if now - timestamp < window
        ]

        # Check if rate limited
        if len(_rate_limits[identifier]) >= max_requests:
            return True

        # Add current request
        _rate_limits[identifier].append(now)
        return False

    def validate_request_size(self, request: Request) -> bool:
        """Validate request size."""
        content_length = request.headers.get("content-length")
        # Ensure numeric comparison uses ints so mypy can validate types
        max_req_size = int(cast(Any, self.config.get("max_request_size", 0)))
        return not (content_length and int(content_length) > max_req_size)

    def detect_injection_attempts(self, data: str) -> bool:
        """Detect potential SQL injection or XSS attempts."""
        suspicious_patterns = [
            "' OR '1'='1'",
            "UNION SELECT",
            "DROP TABLE",
            "DELETE FROM",
            "<script>",
            "javascript:",
            "onerror=",
            "onload=",
            "../",
            "..\\",
            "/etc/passwd",
            "cmd.exe",
        ]

        data_lower = data.lower()
        return any(pattern.lower() in data_lower for pattern in suspicious_patterns)


# Global security manager instance
security_manager = SecurityManager()


def expected_api_key() -> str:
    """
    Get expected API key with priority:
    1) ENV: X_API_KEY or API_KEY
    2) File: data/api_key.secret
    3) Generate new key
    """
    # Try environment variables first
    key = os.getenv("X_API_KEY") or os.getenv("API_KEY")
    if key:
        return key.strip()

    # Try file-based key
    if _KEY_FILE.exists():
        try:
            return _KEY_FILE.read_text().strip()
        except Exception as e:
            security_logger.warning(f"Failed to read API key file: {e}")

    # Generate new key as fallback
    new_key = secrets.token_urlsafe(32)
    try:
        _KEY_FILE.write_text(new_key)
        _META_FILE.write_text(f"Generated: {datetime.now(UTC).isoformat()}\n")
        security_logger.info("Generated new API key")
    except Exception as e:
        security_logger.error(f"Failed to save API key: {e}")

    return new_key


def enforce_api_key(x_api_key: str = Header(None, alias="X-API-Key")) -> bool:
    """FastAPI dependency for API key authentication."""
    expected = expected_api_key()

    if not x_api_key:
        security_manager.log_security_event(
            SecurityEventType.UNAUTHORIZED_ACCESS, {"reason": "Missing API key"}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="API key required"
        )

    if not hmac.compare_digest(x_api_key, expected):
        security_manager.log_security_event(
            SecurityEventType.UNAUTHORIZED_ACCESS, {"reason": "Invalid API key"}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
        )

    return True


class UnifiedSecurityMiddleware(BaseHTTPMiddleware):
    """
    Unified security middleware combining all security features:
    - IP blocking & allowlisting
    - Rate limiting
    - Request validation
    - Security headers
    - Threat detection
    - Audit logging
    """

    def __init__(self, app: Any, config: dict[str, Any] | None = None) -> None:
        super().__init__(app)
        self.config = config or SECURITY_CONFIG
        self.security = security_manager

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Any]
    ) -> Any:
        start_time = time.time()

        # Get client IP
        client_ip = self._get_client_ip(request)

        try:
            # 1. IP blocking check
            if self.security.is_ip_blocked(client_ip):
                self.security.log_security_event(
                    SecurityEventType.UNAUTHORIZED_ACCESS,
                    {"reason": "IP blocked", "path": str(request.url.path)},
                    client_ip,
                )
                return JSONResponse(status_code=403, content={"error": "Access denied"})

            # 2. Rate limiting
            rate_limit_key = f"rate_limit:{client_ip}"
            if self.security.is_rate_limited(rate_limit_key):
                self.security.log_security_event(
                    SecurityEventType.RATE_LIMIT_EXCEEDED,
                    {"path": str(request.url.path)},
                    client_ip,
                )
                return JSONResponse(
                    status_code=429,
                    content={"error": "Rate limit exceeded"},
                    headers={"Retry-After": str(self.config["rate_limit_window"])},
                )

            # 3. Request size validation
            if not self.security.validate_request_size(request):
                self.security.log_security_event(
                    SecurityEventType.SUSPICIOUS_REQUEST,
                    {"reason": "Request too large", "path": str(request.url.path)},
                    client_ip,
                )
                return JSONResponse(
                    status_code=413, content={"error": "Request too large"}
                )

            # 4. Input validation for query parameters
            query_string = str(request.url.query)
            if query_string and self.security.detect_injection_attempts(query_string):
                self.security.log_security_event(
                    SecurityEventType.INJECTION_ATTEMPT,
                    {"type": "query_parameter", "path": str(request.url.path)},
                    client_ip,
                )
                return JSONResponse(
                    status_code=400, content={"error": "Invalid request"}
                )

            # 5. Process request
            response = await call_next(request)

            # 6. Add security headers
            self._add_security_headers(response)

            # 7. Log successful request
            processing_time = time.time() - start_time
            if processing_time > 5.0:  # Log slow requests
                self.security.log_security_event(
                    SecurityEventType.SUSPICIOUS_REQUEST,
                    {
                        "reason": "Slow request",
                        "time": processing_time,
                        "path": str(request.url.path),
                    },
                    client_ip,
                )

            return response

        except Exception as e:
            # Log security-relevant errors
            self.security.log_security_event(
                SecurityEventType.SUSPICIOUS_REQUEST,
                {
                    "reason": "Request processing error",
                    "error": str(e),
                    "path": str(request.url.path),
                },
                client_ip,
            )
            return JSONResponse(
                status_code=500, content={"error": "Internal server error"}
            )

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP with proxy header support."""
        # Check forwarded headers (for reverse proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # Fallback to direct connection
        return str(request.client.host) if request.client else "unknown"

    def _add_security_headers(self, response: Response) -> None:
        """Add comprehensive security headers."""
        security_headers = {
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": (
                "default-src 'self'; script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'"
            ),
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            "X-Permitted-Cross-Domain-Policies": "none",
        }

        for header, value in security_headers.items():
            response.headers[header] = value


# Audit logging functionality
class AuditLogger:
    """Centralized audit logging for security events."""

    def __init__(self):
        self.logger = logging.getLogger("klerno.audit")
        self.logger.setLevel(logging.INFO)

    def log_event(self, event: AuditEvent) -> None:
        """Log an audit event."""
        entry = {
            "event_type": event.event_type,
            "outcome": event.outcome,
            "details": event.details,
            "user_id": event.user_id,
            "timestamp": event.timestamp.isoformat(),
        }

        # Log to system logger (string summary + structured debug)
        self.logger.info(f"{event.event_type} - {event.outcome}")
        self.logger.debug(entry)

        # Log detailed info for debugging
        if event.details:
            self.logger.debug(f"Event details: {event.details}")

    def log_auth_success(self, user: str, ip: str) -> None:
        """Log successful authentication."""
        self.logger.info(f"AUTH_SUCCESS: user={user} ip={ip}")

    def log_auth_failure(self, user: str, ip: str, reason: str) -> None:
        """Log failed authentication."""
        self.logger.warning(f"AUTH_FAILURE: user={user} ip={ip} reason={reason}")
        security_manager.log_security_event(
            SecurityEventType.FAILED_LOGIN, {"user": user, "reason": reason}, ip
        )

    def log_admin_action(
        self, user: str, action: str, target: str | None = None
    ) -> None:
        """Log administrative actions."""
        self.logger.info(f"ADMIN_ACTION: user={user} action={action} target={target}")
        security_manager.log_security_event(
            SecurityEventType.ADMIN_ACCESS,
            {"user": user, "action": action, "target": target},
        )

    def log_data_access(self, user: str, resource: str, action: str) -> None:
        """Log data access events."""
        self.logger.info(
            f"DATA_ACCESS: user={user} resource={resource} action={action}"
        )
        security_manager.log_security_event(
            SecurityEventType.DATA_ACCESS,
            {"user": user, "resource": resource, "action": action},
        )


# Global instances
audit_logger = AuditLogger()

# Legacy compatibility exports (for gradual migration)
SecurityMiddleware = UnifiedSecurityMiddleware  # Alias for existing code

# Export public interface
__all__ = [
    "SecurityManager",
    "UnifiedSecurityMiddleware",
    "SecurityMiddleware",  # Legacy alias
    "AuditLogger",
    "AuditEvent",
    "AuditEventType",
    "SecurityEventType",
    "expected_api_key",
    "enforce_api_key",
    "security_manager",
    "audit_logger",
]
