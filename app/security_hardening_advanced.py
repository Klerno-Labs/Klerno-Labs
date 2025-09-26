"""
Klerno Labs - Advanced Security Hardening Module
Enterprise-grade security for 0.01% quality applications
"""

import base64
import json
import logging
import re
import sqlite3
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


@dataclass
class SecurityEvent:
    """Security event data structure."""

    timestamp: datetime
    event_type: str
    severity: str  # low, medium, high, critical
    source_ip: str
    user_agent: str
    endpoint: str
    details: dict[str, Any]
    blocked: bool = False


@dataclass
class ThreatIntelligence:
    """Threat intelligence data."""

    ip_address: str
    threat_type: str
    confidence: float
    first_seen: datetime
    last_seen: datetime
    country: str | None = None
    description: str | None = None


class AdvancedSecurityHardening:
    """Advanced security hardening with real-time threat detection."""

    def __init__(self, db_path: str = "./data/security.db"):
        self.db_path = db_path
        # rate_limits stores timestamps (floats) per IP
        self.rate_limits: dict[str, deque[float]] = defaultdict(deque)
        self.blocked_ips: set[str] = set()
        self.threat_intel: dict[str, ThreatIntelligence] = {}
        self.security_events: list[SecurityEvent] = []
        self.failed_attempts: dict[str, list[datetime]] = defaultdict(list)

        # Security thresholds
        self.max_requests_per_minute = 100
        self.max_failed_attempts = 5
        self.lockout_duration = timedelta(minutes=15)
        self.suspicious_patterns = [
            r"(\.\./){3,}",  # Directory traversal
            r"<script.*?>.*?</script>",  # XSS attempts
            r"(union|select|insert|delete|drop|create|alter)\s+",  # SQL injection
            r"(eval|exec|system|shell_exec)\s*\(",  # Code injection
            r"(javascript:|data:|vbscript:)",  # Protocol injection
        ]

        # Initialize security database
        self._init_security_database()
        self._load_threat_intelligence()

        # Initialize encryption
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher = Fernet(self.encryption_key)

    def _init_security_database(self) -> None:
        """Initialize security monitoring database."""
        Path(self.db_path).parent.mkdir(exist_ok=True, parents=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Security events table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS security_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                source_ip TEXT NOT NULL,
                user_agent TEXT,
                endpoint TEXT,
                details TEXT,
                blocked BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Threat intelligence table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS threat_intelligence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT UNIQUE NOT NULL,
                threat_type TEXT NOT NULL,
                confidence REAL NOT NULL,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                country TEXT,
                description TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Blocked IPs table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS blocked_ips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT UNIQUE NOT NULL,
                reason TEXT NOT NULL,
                blocked_at TEXT NOT NULL,
                expires_at TEXT,
                permanent BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Failed authentication attempts
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS failed_auth_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT NOT NULL,
                username TEXT,
                endpoint TEXT NOT NULL,
                user_agent TEXT,
                timestamp TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Create indexes for performance
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_security_events_ip ON security_events(source_ip)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_security_events_timestamp ON security_events(timestamp)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_threat_intel_ip ON threat_intelligence(ip_address)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_blocked_ips_ip ON blocked_ips(ip_address)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_failed_auth_ip ON failed_auth_attempts(ip_address)"
        )

        conn.commit()
        conn.close()

    logger.info("[OK] Security database initialized")

    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for sensitive data."""
        key_file = Path("./data/encryption.key")

        if key_file.exists():
            with key_file.open("rb") as f:
                return f.read()
        else:
            # Generate new key
            key = Fernet.generate_key()
            key_file.parent.mkdir(exist_ok=True, parents=True)
            with key_file.open("wb") as f:
                f.write(key)
            logger.info("🔐 Generated new encryption key")
            return key

    def _load_threat_intelligence(self) -> None:
        """Load threat intelligence from database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM threat_intelligence")
            for row in cursor.fetchall():
                threat = ThreatIntelligence(
                    ip_address=row[1],
                    threat_type=row[2],
                    confidence=row[3],
                    first_seen=datetime.fromisoformat(row[4]),
                    last_seen=datetime.fromisoformat(row[5]),
                    country=row[6],
                    description=row[7],
                )
                self.threat_intel[threat.ip_address] = threat

            # Load blocked IPs
            cursor.execute(
                """
                SELECT ip_address FROM blocked_ips
                WHERE expires_at IS NULL OR expires_at > ?
            """,
                (datetime.now().isoformat(),),
            )

            for row in cursor.fetchall():
                self.blocked_ips.add(row[0])

            conn.close()

            loaded_count = len(self.threat_intel)
            blocked_count = len(self.blocked_ips)
            logger.info(
                f"[OK] Loaded {loaded_count} threat indicators and {blocked_count} blocked IPs"
            )

        except Exception as e:
            logger.error(f"Error loading threat intelligence: {e}")

    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data."""
        try:
            encrypted = self.cipher.encrypt(data.encode())
            return base64.b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            return data

    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        try:
            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            decrypted = self.cipher.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            return encrypted_data

    def is_ip_blocked(self, ip_address: str) -> bool:
        """Check if IP address is blocked."""
        return ip_address in self.blocked_ips

    def block_ip(
        self, ip_address: str, reason: str, duration: timedelta | None = None
    ) -> None:
        """Block an IP address."""
        self.blocked_ips.add(ip_address)

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            blocked_at = datetime.now()
            expires_at = blocked_at + duration if duration else None

            cursor.execute(
                """
                INSERT OR REPLACE INTO blocked_ips
                (ip_address, reason, blocked_at, expires_at, permanent)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    ip_address,
                    reason,
                    blocked_at.isoformat(),
                    expires_at.isoformat() if expires_at else None,
                    duration is None,
                ),
            )

            conn.commit()
            conn.close()

            logger.warning(f"🚫 Blocked IP {ip_address}: {reason}")

        except Exception as e:
            logger.error(f"Error blocking IP {ip_address}: {e}")

    def check_rate_limit(
        self, ip_address: str, max_requests: int | None = None
    ) -> bool:
        """Check if IP is within rate limits."""
        max_requests = max_requests or self.max_requests_per_minute
        now = time.time()
        minute_ago = now - 60

        # Clean old requests
        while (
            self.rate_limits[ip_address]
            and self.rate_limits[ip_address][0] < minute_ago
        ):
            self.rate_limits[ip_address].popleft()

        # Check current count
        current_requests = len(self.rate_limits[ip_address])

        if current_requests >= max_requests:
            self.log_security_event(
                event_type="rate_limit_exceeded",
                severity="medium",
                source_ip=ip_address,
                details={
                    "requests_per_minute": current_requests,
                    "limit": max_requests,
                },
            )
            return False

        # Add current request
        self.rate_limits[ip_address].append(now)
        return True

    def detect_suspicious_patterns(self, request_data: dict[str, Any]) -> list[str]:
        """Detect suspicious patterns in request data."""
        suspicious_findings: list[str] = []

        # Check URL path
        path = request_data.get("path", "")
        for pattern in self.suspicious_patterns:
            if re.search(pattern, path, re.IGNORECASE):
                suspicious_findings.append(f"Suspicious pattern in path: {pattern}")

        # Check query parameters
        query_params = request_data.get("query_params", {})
        for key, value in query_params.items():
            for pattern in self.suspicious_patterns:
                if re.search(pattern, str(value), re.IGNORECASE):
                    suspicious_findings.append(
                        f"Suspicious pattern in parameter {key}: {pattern}"
                    )

        # Check headers
        headers = request_data.get("headers", {})
        for header, value in headers.items():
            if header.lower() in ["user-agent", "referer", "x-forwarded-for"]:
                for pattern in self.suspicious_patterns:
                    if re.search(pattern, str(value), re.IGNORECASE):
                        suspicious_findings.append(
                            f"Suspicious pattern in header {header}: {pattern}"
                        )

        # Check for common attack indicators
        combined_data = f"{path} {json.dumps(query_params)} {json.dumps(headers)}"

        # SQL injection indicators
        sql_keywords = [
            "union",
            "select",
            "insert",
            "delete",
            "drop",
            "alter",
            "create",
            "exec",
        ]
        for keyword in sql_keywords:
            if re.search(rf"\b{keyword}\b", combined_data, re.IGNORECASE):
                suspicious_findings.append(f"SQL injection keyword detected: {keyword}")

        # XSS indicators
        xss_patterns = ["<script", "javascript:", "onerror=", "onload=", "eval("]
        for pattern in xss_patterns:
            if pattern.lower() in combined_data.lower():
                suspicious_findings.append(f"XSS pattern detected: {pattern}")

        return suspicious_findings

    def analyze_user_agent(self, user_agent: str) -> dict[str, Any]:
        """Analyze user agent for suspicious characteristics."""
        analysis: dict[str, Any] = {"suspicious": False, "reasons": [], "risk_score": 0}

        if not user_agent or user_agent.strip() == "":
            analysis["suspicious"] = True
            analysis["reasons"].append("Empty user agent")
            analysis["risk_score"] += 30

        # Check for common bot patterns
        bot_patterns = [
            "bot",
            "crawler",
            "spider",
            "scraper",
            "curl",
            "wget",
            "python-requests",
            "go-http-client",
            "http_request",
            "scanner",
            "nikto",
            "sqlmap",
            "nmap",
        ]

        for pattern in bot_patterns:
            if pattern.lower() in user_agent.lower():
                analysis["suspicious"] = True
                analysis["reasons"].append(f"Bot pattern detected: {pattern}")
                analysis["risk_score"] += 20

        # Check for suspicious characteristics
        if len(user_agent) > 500:
            analysis["suspicious"] = True
            analysis["reasons"].append("Unusually long user agent")
            analysis["risk_score"] += 15

        if len(user_agent) < 10:
            analysis["suspicious"] = True
            analysis["reasons"].append("Unusually short user agent")
            analysis["risk_score"] += 25

        return analysis

    def check_geolocation_risk(self, ip_address: str) -> dict[str, Any]:
        """Check IP geolocation risk (placeholder for real geolocation service)."""
        # In production, integrate with a real geolocation service

        # Placeholder logic - in production, use actual geolocation API
        reasons: list[str] = []
        risk_analysis: dict[str, Any] = {
            "country": "Unknown",
            "high_risk": False,
            "risk_score": 0,
            "reasons": reasons,
        }

        # Check if IP is in threat intelligence
        if ip_address in self.threat_intel:
            threat = self.threat_intel[ip_address]
            risk_analysis["high_risk"] = True
            risk_analysis["risk_score"] = threat.confidence * 100
            risk_analysis["reasons"].append(f"Known threat: {threat.threat_type}")
            if threat.country:
                risk_analysis["country"] = threat.country

        return risk_analysis

    def log_security_event(
        self,
        event_type: str,
        severity: str,
        source_ip: str,
        user_agent: str = "",
        endpoint: str = "",
        details: dict[str, Any] | None = None,
        blocked: bool = False,
    ) -> None:
        """Log a security event."""
        event = SecurityEvent(
            timestamp=datetime.now(),
            event_type=event_type,
            severity=severity,
            source_ip=source_ip,
            user_agent=user_agent,
            endpoint=endpoint,
            details=details or {},
            blocked=blocked,
        )

        self.security_events.append(event)

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO security_events
                (timestamp, event_type, severity, source_ip, user_agent, endpoint, details, blocked)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    event.timestamp.isoformat(),
                    event.event_type,
                    event.severity,
                    event.source_ip,
                    event.user_agent,
                    event.endpoint,
                    json.dumps(event.details),
                    event.blocked,
                ),
            )

            conn.commit()
            conn.close()

            if severity in ["high", "critical"]:
                logger.warning(
                    f"🚨 Security event: {event_type} from {source_ip} - {severity}"
                )

        except Exception as e:
            logger.error(f"Error logging security event: {e}")

    def log_failed_auth_attempt(
        self,
        ip_address: str,
        username: str | None = None,
        endpoint: str = "",
        user_agent: str = "",
    ) -> bool:
        """Log failed authentication attempt and check for brute force."""
        now = datetime.now()

        # Clean old attempts (older than 1 hour)
        cutoff = now - timedelta(hours=1)
        self.failed_attempts[ip_address] = [
            attempt for attempt in self.failed_attempts[ip_address] if attempt > cutoff
        ]

        # Add current attempt
        self.failed_attempts[ip_address].append(now)

        # Log to database
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO failed_auth_attempts
                (ip_address, username, endpoint, user_agent, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """,
                (ip_address, username, endpoint, user_agent, now.isoformat()),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Error logging failed auth attempt: {e}")

        # Check for brute force
        attempts_count = len(self.failed_attempts[ip_address])
        if attempts_count >= self.max_failed_attempts:
            self.block_ip(
                ip_address,
                f"Brute force attack detected ({attempts_count} failed attempts)",
                self.lockout_duration,
            )

            self.log_security_event(
                event_type="brute_force_attack",
                severity="high",
                source_ip=ip_address,
                user_agent=user_agent,
                endpoint=endpoint,
                details={
                    "failed_attempts": attempts_count,
                    "username": username,
                    "blocked": True,
                },
                blocked=True,
            )

            return True  # IP was blocked

        return False  # IP not blocked

    def analyze_request_security(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Comprehensive request security analysis."""
        ip_address = request_data.get("client_ip", "")
        user_agent = request_data.get("user_agent", "")
        path = request_data.get("path", "")

        analysis: dict[str, Any] = {
            "blocked": False,
            "risk_score": 0,
            "findings": [],
            "actions_taken": [],
        }

        # Check if IP is already blocked
        if self.is_ip_blocked(ip_address):
            analysis["blocked"] = True
            analysis["findings"].append("IP address is blocked")
            analysis["risk_score"] = 100
            return analysis

        # Check rate limiting
        if not self.check_rate_limit(ip_address):
            analysis["findings"].append("Rate limit exceeded")
            analysis["risk_score"] += 40

            # Block IP for rate limiting abuse
            self.block_ip(ip_address, "Rate limiting abuse", timedelta(minutes=5))
            analysis["blocked"] = True
            analysis["actions_taken"].append("IP blocked for rate limiting abuse")

        # Analyze user agent
        ua_analysis = self.analyze_user_agent(user_agent)
        if ua_analysis["suspicious"]:
            analysis["findings"].extend(ua_analysis["reasons"])
            analysis["risk_score"] += ua_analysis["risk_score"]

        # Check for suspicious patterns
        suspicious_patterns = self.detect_suspicious_patterns(request_data)
        if suspicious_patterns:
            analysis["findings"].extend(suspicious_patterns)
            analysis["risk_score"] += len(suspicious_patterns) * 25

        # Geolocation risk check
        geo_risk = self.check_geolocation_risk(ip_address)
        if geo_risk["high_risk"]:
            analysis["findings"].extend(geo_risk["reasons"])
            analysis["risk_score"] += geo_risk["risk_score"]

        # Log high-risk requests
        if analysis["risk_score"] >= 70:
            severity = "critical" if analysis["risk_score"] >= 90 else "high"
            self.log_security_event(
                event_type="high_risk_request",
                severity=severity,
                source_ip=ip_address,
                user_agent=user_agent,
                endpoint=path,
                details={
                    "risk_score": analysis["risk_score"],
                    "findings": analysis["findings"],
                },
            )

            # Auto-block very high risk requests
            if analysis["risk_score"] >= 90:
                self.block_ip(
                    ip_address, f"Automated block: risk score {analysis['risk_score']}"
                )
                analysis["blocked"] = True
                analysis["actions_taken"].append("IP auto-blocked for high risk")

        return analysis

    def get_security_dashboard_data(self, hours: int = 24) -> dict[str, Any]:
        """Get security dashboard data."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            since = datetime.now() - timedelta(hours=hours)

            # Get security events summary
            cursor.execute(
                """
                SELECT event_type, severity, COUNT(*) as count
                FROM security_events
                WHERE timestamp >= ?
                GROUP BY event_type, severity
                ORDER BY count DESC
            """,
                (since.isoformat(),),
            )

            events_summary: dict[str, dict[str, int]] = {}
            for row in cursor.fetchall():
                event_type = row[0]
                if event_type not in events_summary:
                    events_summary[event_type] = {}
                events_summary[event_type][row[1]] = row[2]

            # Get top blocked IPs
            cursor.execute(
                """
                SELECT source_ip, COUNT(*) as event_count
                FROM security_events
                WHERE timestamp >= ? AND blocked = 1
                GROUP BY source_ip
                ORDER BY event_count DESC
                LIMIT 10
            """,
                (since.isoformat(),),
            )

            top_blocked_ips: list[dict[str, int]] = [
                {"ip": row[0], "events": row[1]} for row in cursor.fetchall()
            ]

            # Get failed auth attempts
            cursor.execute(
                """
                SELECT COUNT(*) FROM failed_auth_attempts
                WHERE timestamp >= ?
            """,
                (since.isoformat(),),
            )

            failed_auth_count = cursor.fetchone()[0]

            # Get active blocks
            cursor.execute(
                """
                SELECT COUNT(*) FROM blocked_ips
                WHERE expires_at IS NULL OR expires_at > ?
            """,
                (datetime.now().isoformat(),),
            )

            active_blocks_count = cursor.fetchone()[0]

            conn.close()

            return {
                "timestamp": datetime.now().isoformat(),
                "events_summary": events_summary,
                "top_blocked_ips": top_blocked_ips,
                "failed_auth_attempts": failed_auth_count,
                "active_blocks": active_blocks_count,
                "threat_intel_entries": len(self.threat_intel),
                "security_status": "secure",
            }

        except Exception as e:
            logger.error(f"Error getting security dashboard data: {e}")
            return {"error": str(e)}


# Global security hardening instance
security_hardening = AdvancedSecurityHardening()


def get_security_hardening() -> AdvancedSecurityHardening:
    """Get the global security hardening instance."""
    return security_hardening
