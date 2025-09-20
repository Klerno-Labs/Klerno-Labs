"""
Advanced Security Middleware
Implements comprehensive security headers and protection measures
"""

import asyncio
import logging
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Advanced rate limiting middleware with sliding window"""

    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients: dict[str, List[float]] = {}
        self.blocked_ips: set[str] = set()

    async def dispatch(self, request: Request, call_next):
        client_ip = self._get_client_ip(request)

        # Check if IP is blocked
        if client_ip in self.blocked_ips:
            return JSONResponse(
                status_code=429,
                content={"detail": "IP temporarily blocked due to abuse"},
            )

        # Rate limiting logic
        now = time.time()
        if client_ip not in self.clients:
            self.clients[client_ip] = []

        # Remove old requests outside the window
        self.clients[client_ip] = [
            req_time
            for req_time in self.clients[client_ip]
            if now - req_time < self.period
        ]

        # Check if limit exceeded
        if len(self.clients[client_ip]) >= self.calls:
            # Block IP for 5 minutes if consistently over limit
            self.blocked_ips.add(client_ip)
            asyncio.create_task(self._unblock_ip_later(client_ip, 300))

            return JSONResponse(
                status_code=429, content={"detail": "Rate limit exceeded"}
            )

        # Add current request
        self.clients[client_ip].append(now)

        response = await call_next(request)
        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        return request.client.host if request.client else "unknown"

    async def _unblock_ip_later(self, ip: str, delay: int):
        """Unblock IP after specified delay"""
        await asyncio.sleep(delay)
        self.blocked_ips.discard(ip)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds comprehensive security headers to all responses"""

    def __init__(self, app):
        super().__init__(app)
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            "X-Permitted-Cross-Domain-Policies": "none",
            "Cross-Origin-Embedder-Policy": "require-corp",
            "Cross-Origin-Opener-Policy": "same-origin",
            "Cross-Origin-Resource-Policy": "same-origin",
        }

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Add security headers
        for header, value in self.security_headers.items():
            response.headers[header] = value

        # Remove server identification
        response.headers.pop("server", None)

        return response


class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """Sanitizes and validates all input data"""

    def __init__(self, app):
        super().__init__(app)
        self.suspicious_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"vbscript:",
            r"onload=",
            r"onerror=",
            r"onclick=",
            r"eval\(",
            r"expression\(",
            r"url\(",
            r"@import",
            r"<iframe",
            r"<object",
            r"<embed",
            r"<link",
        ]

    async def dispatch(self, request: Request, call_next):
        # Log suspicious requests
        if self._is_suspicious_request(request):
            logging.warning(
                f"Suspicious request detected from {request.client.host}: {request.url}"
            )

        response = await call_next(request)
        return response

    def _is_suspicious_request(self, request: Request) -> bool:
        """Check if request contains suspicious patterns"""
        import re

        # Check URL
        url_str = str(request.url)
        for pattern in self.suspicious_patterns:
            if re.search(pattern, url_str, re.IGNORECASE):
                return True

        # Check headers
        for header_value in request.headers.values():
            for pattern in self.suspicious_patterns:
                if re.search(pattern, header_value, re.IGNORECASE):
                    return True

        return False


class APIKeyValidationMiddleware(BaseHTTPMiddleware):
    """Enhanced API key validation with rate limiting per key"""

    def __init__(self, app):
        super().__init__(app)
        self.api_key_usage: dict[str, List[float]] = {}
        self.key_limits = {
            "basic": {"calls": 100, "period": 3600},
            "premium": {"calls": 1000, "period": 3600},
            "enterprise": {"calls": 10000, "period": 3600},
        }

    async def dispatch(self, request: Request, call_next):
        # Skip middleware for non-API routes
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return JSONResponse(status_code=401, content={"detail": "API key required"})

        # Validate API key and check rate limits
        key_tier = self._validate_api_key(api_key)
        if not key_tier:
            return JSONResponse(status_code=401, content={"detail": "Invalid API key"})

        # Check rate limits for this key
        if not self._check_rate_limit(api_key, key_tier):
            return JSONResponse(
                status_code=429, content={"detail": "API key rate limit exceeded"}
            )

        response = await call_next(request)
        return response

    def _validate_api_key(self, api_key: str) -> str | None:
        """Validate API key and return tier"""
        # This would integrate with your actual API key storage
        # For now, return a default tier
        if len(api_key) >= 32:  # Basic validation
            return "basic"
        return None

    def _check_rate_limit(self, api_key: str, tier: str) -> bool:
        """Check if API key is within rate limits"""
        now = time.time()
        limit_config = self.key_limits.get(tier, self.key_limits["basic"])

        if api_key not in self.api_key_usage:
            self.api_key_usage[api_key] = []

        # Remove old requests
        self.api_key_usage[api_key] = [
            req_time
            for req_time in self.api_key_usage[api_key]
            if now - req_time < limit_config["period"]
        ]

        # Check limit
        if len(self.api_key_usage[api_key]) >= limit_config["calls"]:
            return False

        # Add current request
        self.api_key_usage[api_key].append(now)
        return True
