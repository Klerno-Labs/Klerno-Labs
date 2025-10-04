# Provide a getter for analytics_dashboard compatibility
def get_security_middleware() -> None:
    global security_middleware
    if not security_middleware:
        security_middleware = AdvancedSecurityMiddleware(None)
    return security_middleware


"""
Advanced Security Hardening for Klerno Labs
Enhanced rate limiting, IP whitelisting, and threat protection
"""

import contextlib
import ipaddress
import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class ThreatLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityEvent:
    ip: str
    timestamp: float
    event_type: str
    threat_level: ThreatLevel
    details: dict[str, Any]
    blocked: bool = False


class AdvancedRateLimiter:
    """Advanced rate limiting with different strategies"""

    def __init__(self) -> None:
        self.requests = defaultdict(deque)  # IP -> deque of timestamps
        self.blocked_ips = defaultdict(float)  # IP -> unblock_time
        self.failed_attempts = defaultdict(int)  # IP -> failed_count
        self.suspicious_patterns = defaultdict(list[Any])  # IP -> patterns

    def is_rate_limited(self, ip: str, endpoint: str, limit: int, window: int) -> bool:
        """Check if IP is rate limited for specific endpoint"""
        now = time.time()

        # Check if IP is temporarily blocked
        if ip in self.blocked_ips and now < self.blocked_ips[ip]:
            return True

        # Clean old requests
        key = f"{ip}:{endpoint}"
        request_times = self.requests[key]

        # Remove requests outside the window
        while request_times and request_times[0] < now - window:
            request_times.popleft()

        # Check if limit exceeded
        if len(request_times) >= limit:
            return True

        # Add current request
        request_times.append(now)
        return False

    def block_ip(self, ip: str, duration: int) -> None:
        """Temporarily block an IP address"""
        self.blocked_ips[ip] = time.time() + duration

    def add_failed_attempt(self, ip: str) -> int:
        """Track failed login attempts"""
        self.failed_attempts[ip] += 1
        return self.failed_attempts[ip]

    def clear_failed_attempts(self, ip: str) -> None:
        """Clear failed attempts for successful login"""
        if ip in self.failed_attempts:
            del self.failed_attempts[ip]


class IPWhitelist:
    """Advanced IP whitelisting with CIDR support"""

    def __init__(self) -> None:
        self.whitelist: set[str] = set()
        self.whitelist_networks: list[ipaddress.IPv4Network] = []
        self.admin_whitelist: set[str] = set()
        self.api_whitelist: set[str] = set()

        # Add default safe networks
        self.add_network("127.0.0.0/8")  # Localhost
        self.add_network("10.0.0.0/8")  # Private network
        self.add_network("172.16.0.0/12")  # Private network
        self.add_network("192.168.0.0/16")  # Private network

    def add_ip(self, ip: str, category: str = "general") -> None:
        """Add IP to whitelist"""
        if category == "admin":
            self.admin_whitelist.add(ip)
        elif category == "api":
            self.api_whitelist.add(ip)
        else:
            self.whitelist.add(ip)

    def add_network(self, network: str) -> None:
        """Add network CIDR to whitelist"""
        with contextlib.suppress(ValueError):
            self.whitelist_networks.append(ipaddress.IPv4Network(network))

    def is_whitelisted(self, ip: str, category: str = "general") -> bool:
        """Check if IP is whitelisted"""
        # Check direct IP whitelist
        if category == "admin" and ip in self.admin_whitelist:
            return True
        if category == "api" and ip in self.api_whitelist:
            return True
        if ip in self.whitelist:
            return True

        # Check network whitelist
        try:
            ip_addr = ipaddress.IPv4Address(ip)
            for network in self.whitelist_networks:
                if ip_addr in network:
                    return True
        except ValueError:
            pass

        return False


class ThreatDetector:
    """Advanced threat detection and analysis"""

    def __init__(self) -> None:
        self.malicious_ips: set[str] = set()
        self.suspicious_user_agents: list[str] = [
            "sqlmap",
            "nikto",
            "dirb",
            "gobuster",
            "wfuzz",
            "masscan",
            "zmap",
            "nmap",
            "burp",
            "owasp",
        ]
        self.attack_patterns = {
            "sql_injection": re.compile(
                r"(\bunion\b.*\bselect\b|\bselect\b.*\bfrom\b|\'.*or.*\'|\".*or.*\")",
                re.IGNORECASE,
            ),
            "xss": re.compile(
                r"(<script.*?>|javascript:|onload=|onerror=)",
                re.IGNORECASE,
            ),
            "path_traversal": re.compile(
                r"(\.\./|\.\.\\\\|%2e%2e%2f|%2e%2e%5c)",
                re.IGNORECASE,
            ),
            "command_injection": re.compile(r"(;|\||&|\$\(|\`)", re.IGNORECASE),
        }
        self.security_events: list[SecurityEvent] = []

    def detect_threats(self, request: Request) -> list[SecurityEvent]:
        """Detect various threats in the request"""
        threats = []
        ip = self.get_client_ip(request)

        # Check malicious IP
        if ip in self.malicious_ips:
            threats.append(
                SecurityEvent(
                    ip=ip,
                    timestamp=time.time(),
                    event_type="malicious_ip",
                    threat_level=ThreatLevel.HIGH,
                    details={"reason": "Known malicious IP"},
                ),
            )

        # Check user agent
        user_agent = request.headers.get("user-agent", "").lower()
        for suspicious_ua in self.suspicious_user_agents:
            if suspicious_ua in user_agent:
                threats.append(
                    SecurityEvent(
                        ip=ip,
                        timestamp=time.time(),
                        event_type="suspicious_user_agent",
                        threat_level=ThreatLevel.MEDIUM,
                        details={"user_agent": user_agent, "pattern": suspicious_ua},
                    ),
                )

        # Check for attack patterns in URL and parameters
        full_url = str(request.url)
        for attack_type, pattern in self.attack_patterns.items():
            if pattern.search(full_url):
                threats.append(
                    SecurityEvent(
                        ip=ip,
                        timestamp=time.time(),
                        event_type=f"attack_pattern_{attack_type}",
                        threat_level=ThreatLevel.HIGH,
                        details={"url": full_url, "attack_type": attack_type},
                    ),
                )

        # Log all threats
        self.security_events.extend(threats)

        return threats

    def get_client_ip(self, request: Request) -> str:
        """Get real client IP considering proxies"""
        # Check X-Forwarded-For header first (for proxies/load balancers)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()

        # Check X-Real-IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fallback to direct connection IP
        return request.client.host if request.client else "127.0.0.1"

    def add_malicious_ip(self, ip: str) -> None:
        """Add IP to malicious list[Any]"""
        self.malicious_ips.add(ip)

    def get_recent_events(self, hours: int = 24) -> list[SecurityEvent]:
        """Get recent security events"""
        cutoff = time.time() - (hours * 3600)
        return [event for event in self.security_events if event.timestamp > cutoff]


class AdvancedSecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive security middleware"""

    def __init__(self, app) -> None:
        super().__init__(app)
        self.rate_limiter = AdvancedRateLimiter()
        self.ip_whitelist = IPWhitelist()
        self.threat_detector = ThreatDetector()

        # Rate limiting rules
        self.rate_limits = {
            # General limits
            "general": {"limit": 100, "window": 60},  # 100 requests per minute
            "api": {"limit": 1000, "window": 3600},  # 1000 API calls per hour
            # Authentication limits
            "/auth/login": {
                "limit": 5,
                "window": 300,
            },  # 5 login attempts per 5 minutes
            "/auth/signup": {"limit": 3, "window": 3600},  # 3 signups per hour
            "/auth/forgot-password": {"limit": 3, "window": 3600},
            # Admin limits
            "/admin": {"limit": 50, "window": 3600},  # 50 admin requests per hour
            # Sensitive endpoints
            "/api/analyze": {"limit": 10, "window": 60},  # 10 analyses per minute
            "/api/upload": {"limit": 5, "window": 300},  # 5 uploads per 5 minutes
        }

    async def dispatch(self, request: Request, call_next) -> Any:
        """Main security dispatch"""
        start_time = time.time()
        ip = self.threat_detector.get_client_ip(request)
        path = request.url.path

        # Skip security checks for health endpoints
        if path in ["/healthz", "/health"]:
            return await call_next(request)

        # Skip security checks in test/dev mode
        import os

        is_test_mode = os.getenv("APP_ENV", "production").lower() in [
            "test",
            "testing",
            "dev",
            "development",
            "local",
        ]
        if is_test_mode:
            return await call_next(request)

        try:
            # 1. Threat Detection
            threats = self.threat_detector.detect_threats(request)
            high_threats = [
                t
                for t in threats
                if t.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]
            ]

            if high_threats:
                # Block request and log
                self.rate_limiter.block_ip(ip, 3600)  # Block for 1 hour
                return JSONResponse(
                    status_code=403,
                    content={"error": "Security threat detected", "blocked": True},
                )

            # 2. IP Whitelisting for sensitive endpoints
            if path.startswith("/admin/") and not self.ip_whitelist.is_whitelisted(
                ip,
                "admin",
            ):
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "Access denied: IP not whitelisted for admin access",
                    },
                )

            # 3. Rate Limiting
            rate_limited = False

            # Check specific endpoint limits
            for endpoint, limits in self.rate_limits.items():
                if (
                    endpoint != "general"
                    and endpoint != "api"
                    and path.startswith(endpoint)
                    and self.rate_limiter.is_rate_limited(
                        ip,
                        endpoint,
                        limits["limit"],
                        limits["window"],
                    )
                ):
                    rate_limited = True
                    break

            # Check general API limits
            if not rate_limited and path.startswith("/api/"):
                api_limits = self.rate_limits["api"]
                if self.rate_limiter.is_rate_limited(
                    ip,
                    "api",
                    api_limits["limit"],
                    api_limits["window"],
                ):
                    rate_limited = True

            # Check general limits
            if not rate_limited:
                general_limits = self.rate_limits["general"]
                if self.rate_limiter.is_rate_limited(
                    ip,
                    "general",
                    general_limits["limit"],
                    general_limits["window"],
                ):
                    rate_limited = True

            if rate_limited:
                return JSONResponse(
                    status_code=429,
                    content={"error": "Rate limit exceeded", "retry_after": 60},
                )

            # 4. Request size limits
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB limit
                return JSONResponse(
                    status_code=413,
                    content={"error": "Request too large"},
                )

            # Process request
            response = await call_next(request)

            # 5. Post-processing security
            if response.status_code in [401, 403]:
                # Track failed auth attempts
                if path.startswith("/auth/"):
                    failed_count = self.rate_limiter.add_failed_attempt(ip)
                    if failed_count >= 10:  # Block after 10 failed attempts
                        self.rate_limiter.block_ip(ip, 1800)  # 30 minutes
            elif response.status_code == 200 and path.startswith("/auth/login"):
                # Clear failed attempts on successful login
                self.rate_limiter.clear_failed_attempts(ip)

            # Add security headers
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

            # Add timing header
            process_time = time.time() - start_time
            response.headers["X-Security-Time"] = str(process_time)

            return response

        except Exception as e:
            # Log security middleware errors
            print(f"Security middleware error: {e}")
            return await call_next(request)


def create_security_config() -> None:
    """Create security configuration"""
    return {
        "rate_limiting": {
            "enabled": True,
            "global_limit": 100,
            "window": 60,
            "fail2ban_enabled": True,
            "fail2ban_threshold": 10,
            "fail2ban_duration": 1800,
        },
        "ip_whitelisting": {"enabled": True, "admin_only": True, "api_whitelist": []},
        "threat_detection": {
            "enabled": True,
            "log_threats": True,
            "auto_block": True,
            "block_duration": 3600,
        },
    }


# Initialize global security components
security_middleware = None


def initialize_security() -> None:
    """Initialize security components"""
    global security_middleware
    if not security_middleware:
        security_middleware = AdvancedSecurityMiddleware(None)
    return security_middleware
