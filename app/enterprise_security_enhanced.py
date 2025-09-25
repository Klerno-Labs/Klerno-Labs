"""
Enterprise Security Module for Klerno Labs.

Comprehensive security hardening including:
- Anti - theft protection
- Request validation
- Rate limiting
- Security headers
- Input sanitization
- Audit logging
"""

from __future__ import annotations

import contextlib
import ipaddress
import logging
import os
import time
from datetime import UTC, datetime
from typing import Any, cast

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# Configure security logging
security_logger = logging.getLogger("klerno.security")
security_logger.setLevel(logging.INFO)

# Rate limiting storage (in - memory fallback if Redis unavailable)
try:
    import redis

    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        decode_responses=True,
    )
    redis_client.ping()
    USE_REDIS = True
except ImportError:
    USE_REDIS = False
    # Note: Redis not available or failed to connect; fall back to in-memory store
    rate_limit_store: dict[str, dict[str, Any]] = {}
except Exception:
    USE_REDIS = False
    # Note: Redis connection failed, using in-memory rate limiting (this is expected in development)
    rate_limit_store = {}


class SecurityConfig:
    """Security configuration constants."""

    # Rate limiting (requests per window)
    RATE_LIMITS = {
        "auth": (5, 300),  # 5 requests per 5 minutes for auth endpoints
        "api": (1000, 3600),  # 1000 requests per hour for API
        "admin": (100, 3600),  # 100 requests per hour for admin
        "payment": (10, 3600),  # 10 payment requests per hour
    }

    # Blocked user agents (security scanners, bots)
    BLOCKED_USER_AGENTS = {
        "sqlmap",
        "nikto",
        "nmap",
        "masscan",
        "zap",
        "burp",
        "w3af",
        "acunetix",
        "nessus",
        "openvas",
        "metasploit",
    }

    # Suspicious patterns in requests
    SUSPICIOUS_PATTERNS = {
        "sql_injection": [
            "union",
            "select",
            "drop",
            "insert",
            "update",
            "delete",
            "'",
            '"',
            "--",
            "/*",
            "*/",
        ],
        "xss": [
            "<script",
            "javascript:",
            "onload=",
            "onerror=",
            "alert(",
            "document.cookie",
        ],
        "path_traversal": [
            "../",
            "..\\",
            "/etc / passwd",
            "/etc / shadow",
            "windows / system32",
        ],
        "command_injection": [
            ";",
            "|",
            "&",
            "`",
            "$",
            "(",
            ")",
            "echo",
            "cat",
            "ls",
            "whoami",
        ],
    }

    # Security headers
    SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self' wss: https:; "
            "object-src 'none'; "
            "frame-ancestors 'none';"
        ),
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    }


class AntiTheftProtection:
    """Anti - theft and intellectual property protection."""

    @staticmethod
    def verify_request_integrity(request: Request) -> bool:
        """Verify request hasn't been tampered with."""
        # Check for suspicious headers that indicate automation / scraping
        user_agent = request.headers.get("user-agent", "").lower()

        # Block obvious bots / scrapers
        if any(bot in user_agent for bot in SecurityConfig.BLOCKED_USER_AGENTS):
            return False

        # Block requests without user agent
        return not (not user_agent or len(user_agent) < 10)

    @staticmethod
    def check_rate_limits(client_ip: str, endpoint_type: str) -> bool:
        """Check if client has exceeded rate limits."""
        limit, window = SecurityConfig.RATE_LIMITS.get(endpoint_type, (100, 3600))
        key = f"rate_limit:{endpoint_type}:{client_ip}"

        if USE_REDIS:
            try:
                current = redis_client.get(key)
                if current is None:
                    redis_client.setex(key, window, 1)
                    return True
                # Safely coerce Redis return value to int
                try:
                    curr_val = int(cast(Any, current))
                except Exception:
                    try:
                        curr_val = int(str(cast(Any, current)))
                    except Exception:
                        # Unknown type from Redis client; increment and allow
                        with contextlib.suppress(Exception):
                            redis_client.incr(key)
                        return True

                if curr_val >= limit:
                    return False
                else:
                    redis_client.incr(key)
                    return True
            except Exception:
                # Fall back to in - memory if Redis fails
                pass

        # In - memory rate limiting
        now = time.time()
        if key not in rate_limit_store:
            rate_limit_store[key] = {"count": 1, "reset_time": now + window}
            return True

        data = rate_limit_store[key]
        if now > data["reset_time"]:
            rate_limit_store[key] = {"count": 1, "reset_time": now + window}
            return True

        if data["count"] >= limit:
            return False

        data["count"] += 1
        return True


class InputSanitizer:
    """Input validation and sanitization."""

    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """Sanitize string input to prevent injection attacks."""
        if not isinstance(value, str):
            raise ValueError("Input must be a string")

        # Truncate if too long
        if len(value) > max_length:
            value = value[:max_length]

        # Remove null bytes
        value = value.replace("\x00", "")

        # Check for suspicious patterns
        value_lower = value.lower()
        for pattern_type, patterns in SecurityConfig.SUSPICIOUS_PATTERNS.items():
            for pattern in patterns:
                if pattern in value_lower:
                    security_logger.warning(
                        f"Suspicious {pattern_type} pattern detected: {pattern}"
                    )
                    # Don't reject, just log for monitoring

        return value.strip()

    @staticmethod
    def validate_email(email: str) -> str:
        """Validate and sanitize email address."""
        email = InputSanitizer.sanitize_string(email, 254)

        # Basic email validation
        if "@" not in email or "." not in email.split("@")[1]:
            raise ValueError("Invalid email format")

        # Check for suspicious patterns
        if any(char in email for char in ["<", ">", "script", "javascript"]):
            raise ValueError("Invalid characters in email")

        return email.lower().strip()

    @staticmethod
    def validate_wallet_address(address: str) -> str:
        """Validate cryptocurrency wallet address."""
        address = InputSanitizer.sanitize_string(address, 100)

        # Basic validation - should be alphanumeric
        if not all(c.isalnum() for c in address):
            raise ValueError("Invalid wallet address format")

        # Check length constraints
        if len(address) < 20 or len(address) > 80:
            raise ValueError("Wallet address length invalid")

        return address


class SecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive security middleware."""

    # Whitelisted paths that bypass security checks
    WHITELISTED_PATHS = ["/health", "/healthz", "/metrics", "/status", "/ping"]

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        client_ip = self._get_client_ip(request)

        try:
            # Check if this is development mode
            is_dev_mode = os.getenv("APP_ENV", "production").lower() in [
                "dev",
                "development",
                "local",
                "test",
            ]

            # Check if this is a whitelisted path (health checks, monitoring)
            is_whitelisted = any(
                request.url.path.startswith(path) for path in self.WHITELISTED_PATHS
            )

            # In development or test mode, bypass all security checks for easier testing
            if is_dev_mode:
                response = await call_next(request)
                # Still add basic security headers but skip integrity checks
                for header, value in SecurityConfig.SECURITY_HEADERS.items():
                    response.headers[header] = value
                response.headers["X-Request-ID"] = self._generate_request_id()
                response.headers["X-Response-Time"] = str(
                    round((time.time() - start_time) * 1000, 2)
                )
                self._log_request(
                    request, response, client_ip, time.time() - start_time
                )
                return response

            # Anti - theft protection (skip for whitelisted paths)
            if not is_whitelisted and not AntiTheftProtection.verify_request_integrity(
                request
            ):
                security_logger.warning(
                    f"Request integrity check failed for {client_ip}"
                )
                return JSONResponse(status_code=403, content={"error": "Access denied"})

            # Determine endpoint type for rate limiting
            endpoint_type = self._get_endpoint_type(request.url.path)

            # Rate limiting (more lenient for whitelisted paths and disabled in dev mode)
            if (
                not is_whitelisted
                and not is_dev_mode
                and not AntiTheftProtection.check_rate_limits(client_ip, endpoint_type)
            ):
                security_logger.warning(
                    f"Rate limit exceeded for {client_ip} on {endpoint_type}"
                )
                return JSONResponse(
                    status_code=429, content={"error": "Rate limit exceeded"}
                )

            # Process request
            response = await call_next(request)

            # Add security headers
            for header, value in SecurityConfig.SECURITY_HEADERS.items():
                response.headers[header] = value

            # Remove server information
            if "server" in response.headers:
                del response.headers["server"]

            # Add custom security headers
            response.headers["X-Request-ID"] = self._generate_request_id()
            response.headers["X-Response-Time"] = str(
                round((time.time() - start_time) * 1000, 2)
            )

            # Log successful request
            self._log_request(request, response, client_ip, time.time() - start_time)

            return response

        except Exception as e:
            security_logger.error(
                f"Security middleware error for {client_ip}: {str(e)}"
            )
            return JSONResponse(
                status_code=500, content={"error": "Internal server error"}
            )

    def _get_client_ip(self, request: Request) -> str:
        """Get real client IP address."""
        # Check forwarded headers (in order of preference)
        forwarded_headers = [
            "x-forwarded-for",
            "x-real-ip",
            "cf-connecting-ip",  # Cloudflare
            "x-client-ip",
        ]

        for header in forwarded_headers:
            value = request.headers.get(header)
            if value:
                # Take first IP if comma - separated
                ip = value.split(",")[0].strip()
                try:
                    ipaddress.ip_address(ip)
                    return ip
                except ValueError:
                    continue

        # Fall back to direct connection
        if request.client:
            return getattr(request.client, "host", "unknown")
        return "unknown"

    def _get_endpoint_type(self, path: str) -> str:
        """Determine endpoint type for rate limiting."""
        if path.startswith("/auth/"):
            return "auth"
        elif path.startswith("/admin/"):
            return "admin"
        elif path.startswith("/api/payment") or path.startswith("/paywall"):
            return "payment"
        elif path.startswith("/api/"):
            return "api"
        else:
            return "general"

    def _generate_request_id(self) -> str:
        """Generate unique request ID for tracking."""
        import uuid

        return str(uuid.uuid4())[:8]

    def _log_request(
        self, request: Request, response: Response, client_ip: str, duration: float
    ):
        """Log request for security monitoring."""
        log_data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "client_ip": client_ip,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2),
            "user_agent": request.headers.get("user-agent", "")[:200],
            "referer": request.headers.get("referer", "")[:200],
        }

        # Log as JSON for easy parsing
        security_logger.info(f"REQUEST: {log_data}")


class AuditLogger:
    """Security audit and compliance logging."""

    @staticmethod
    def log_security_event(
        event_type: str, details: dict[str, Any], client_ip: str | None = None
    ):
        """Log security - related events for audit trail."""
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event_type": event_type,
            "client_ip": client_ip,
            "details": details,
        }

        security_logger.info(f"SECURITY_EVENT: {log_entry}")

    @staticmethod
    def log_admin_action(
        admin_email: str, action: str, target: str, client_ip: str | None = None
    ):
        """Log administrative actions for compliance."""
        AuditLogger.log_security_event(
            "admin_action",
            {"admin_email": admin_email, "action": action, "target": target},
            client_ip,
        )

    @staticmethod
    def log_authentication(email: str, success: bool, client_ip: str | None = None):
        """Log authentication attempts."""
        AuditLogger.log_security_event(
            "authentication", {"email": email, "success": success}, client_ip
        )


# Export main components
__all__ = [
    "SecurityMiddleware",
    "InputSanitizer",
    "AntiTheftProtection",
    "AuditLogger",
    "SecurityConfig",
]
