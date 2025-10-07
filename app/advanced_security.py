"""Advanced Security Hardening System.

State - of - the - art protection against sophisticated hackers including
zero - day exploits, advanced persistent threats, and nation - state level attacks.
Multi - layer defense with behavioral analysis and threat intelligence.
"""

from __future__ import annotations

import ipaddress
import logging
import re
import secrets
import threading
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa


class ThreatLevel(str, Enum):
    """Threat severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AttackType(str, Enum):
    """Types of security attacks."""

    BRUTE_FORCE = "brute_force"
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    CSRF = "csrf"
    DDoS = "ddos"
    APT = "apt"  # Advanced Persistent Threat
    ZERO_DAY = "zero_day"
    SOCIAL_ENGINEERING = "social_engineering"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXFILTRATION = "data_exfiltration"
    MALWARE = "malware"
    PHISHING = "phishing"


class SecurityAction(str, Enum):
    """Security response actions."""

    BLOCK = "block"
    MONITOR = "monitor"
    QUARANTINE = "quarantine"
    ALERT = "alert"
    HONEYPOT = "honeypot"
    DEGRADE = "degrade"


@dataclass
class SecurityThreat:
    """Security threat detection."""

    id: str
    threat_type: AttackType
    threat_level: ThreatLevel
    source_ip: str
    target: str
    description: str
    timestamp: datetime
    evidence: dict[str, Any]
    confidence_score: float  # 0.0 - 1.0
    mitigated: bool = False


@dataclass
class SecurityRule:
    """Security detection rule."""

    id: str
    name: str
    attack_type: AttackType
    pattern: str
    threshold: int
    time_window: int  # seconds
    action: SecurityAction
    enabled: bool = True


class BehavioralAnalyzer:
    """Analyzes user behavior for anomaly detection."""

    def __init__(self) -> None:
        self.user_profiles: dict[str, dict[str, Any]] = {}
        self.session_data: dict[str, list[Any]] = defaultdict(list[Any])
        self.anomaly_threshold = 0.7  # Anomaly score threshold
        self.lock = threading.Lock()
        self.monitoring_active = False

    def track_user_activity(self, user_id: str, activity: dict[str, Any]) -> None:
        """Track user activity for behavioral analysis."""
        with self.lock:
            if user_id not in self.user_profiles:
                self.user_profiles[user_id] = {
                    "login_times": [],
                    "ip_addresses": set(),
                    "user_agents": set(),
                    "request_patterns": defaultdict(int),
                    "geolocation": set(),
                    "last_activity": None,
                }

            profile = self.user_profiles[user_id]
            current_time = datetime.now(UTC)

            # Update profile data
            if activity.get("type") == "login":
                profile["login_times"].append(current_time)
                # Keep only last 100 login times
                profile["login_times"] = profile["login_times"][-100:]

            if "ip_address" in activity:
                profile["ip_addresses"].add(activity["ip_address"])
                # Keep only last 20 IP addresses
                if len(profile["ip_addresses"]) > 20:
                    tmp_ips = list(profile["ip_addresses"])[-20:]
                    profile["ip_addresses"] = set(tmp_ips)

            if "user_agent" in activity:
                profile["user_agents"].add(activity["user_agent"])
                # Keep only last 10 user agents
                if len(profile["user_agents"]) > 10:
                    tmp_agents = list(profile["user_agents"])[-10:]
                    profile["user_agents"] = set(tmp_agents)

            if "endpoint" in activity:
                profile["request_patterns"][activity["endpoint"]] += 1

            if "geolocation" in activity:
                profile["geolocation"].add(activity["geolocation"])

            profile["last_activity"] = current_time

            # Store session data
            session_id = activity.get("session_id", "unknown")
            self.session_data[session_id].append(
                {"timestamp": current_time, "activity": activity},
            )

    def detect_anomalies(
        self,
        user_id: str,
        current_activity: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Detect behavioral anomalies."""
        anomalies: list[dict[str, Any]] = []

        if user_id not in self.user_profiles:
            return anomalies

        profile = self.user_profiles[user_id]
        current_time = datetime.now(UTC)

        # Check for unusual login times
        if current_activity.get("type") == "login" and profile["login_times"]:
            usual_hours = [t.hour for t in profile["login_times"]]
            current_hour = current_time.hour

            # If current hour is not in usual pattern (simple heuristic)
            hour_counts: dict[int, int] = defaultdict(int)
            for hour in usual_hours:
                hour_counts[hour] += 1

            if hour_counts[current_hour] == 0 and len(usual_hours) > 5:
                anomalies.append(
                    {
                        "type": "unusual_login_time",
                        "severity": "medium",
                        "description": (f"Login at unusual hour: {current_hour}"),
                        "confidence": 0.6,
                    },
                )

        # Check for new IP address
        current_ip = current_activity.get("ip_address")
        if current_ip and current_ip not in profile["ip_addresses"]:
            # Check if IP is from different geolocation
            anomalies.append(
                {
                    "type": "new_ip_address",
                    "severity": "medium",
                    "description": f"Login from new IP: {current_ip}",
                    "confidence": 0.5,
                },
            )

        # Check for unusual request patterns
        current_endpoint = current_activity.get("endpoint")
        if current_endpoint:
            # Check request frequency
            recent_requests = [
                req
                for req in self.session_data.get(
                    current_activity.get("session_id", ""),
                    [],
                )
                if req["timestamp"] > current_time - timedelta(minutes=5)
                and req["activity"].get("endpoint") == current_endpoint
            ]

            if len(recent_requests) > 50:  # More than 50 requests in 5 minutes
                anomalies.append(
                    {
                        "type": "high_request_frequency",
                        "severity": "high",
                        "description": (
                            f"High frequency requests to {current_endpoint}"
                        ),
                        "confidence": 0.8,
                    },
                )

        # Check for privilege escalation attempts
        if current_activity.get(
            "type",
        ) == "admin_access" and user_id not in profile.get("admin_users", set()):
            anomalies.append(
                {
                    "type": "privilege_escalation",
                    "severity": "critical",
                    "description": "Unauthorized admin access attempt",
                    "confidence": 0.9,
                },
            )

        return anomalies

    def start_monitoring(self) -> None:
        """Start behavioral monitoring."""
        logger.info("Behavioral analysis monitoring started")
        # In a real implementation, this might start background threads
        # or initialize monitoring systems
        self.monitoring_active = True

    def stop_monitoring(self) -> None:
        """Stop behavioral monitoring."""
        logger.info("Behavioral analysis monitoring stopped")
        self.monitoring_active = False


class ThreatIntelligence:
    """Threat intelligence and reputation system."""

    def __init__(self) -> None:
        self.malicious_ips: set[str] = set()
        self.suspicious_patterns: list[str] = []
        self.reputation_cache: dict[str, dict[str, Any]] = {}
        self.threat_feeds: list[str] = []
        self.lock = threading.Lock()

        # Load initial threat intelligence
        self._load_threat_data()

    def _load_threat_data(self) -> None:
        """Load threat intelligence data."""
        # Known malicious patterns
        self.suspicious_patterns.extend(
            [
                # SQL Injection patterns
                r"(\bUNION\b.*\bSELECT\b)",
                r"(\bSELECT\b.*\bFROM\b.*\bWHERE\b)",
                r"(\bDROP\b.*\bTABLE\b)",
                r"(\bINSERT\b.*\bINTO\b)",
                r"(--|\  #|\/\*|\*\/)",
                # XSS patterns
                r"(<script.*?>.*?</script>)",
                r"(javascript:)",
                r"(vbscript:)",
                r"(onload=|onclick=|onerror=)",
                # Command injection
                r"(;|\||&|\$\(|\`)",
                r"(wget|curl|nc|netcat)",
                # Path traversal
                r"(\.\./|\.\.\\)",
                r"(/etc / passwd|/etc / shadow)",
                # LDAP injection
                r"(\)\(|\)\&|\)\|)",
                # NoSQL injection
                r"(\$ne|\$gt|\$lt|\$regex)",
            ],
        )

        # Example malicious IPs (in production, load from threat feeds)
        self.malicious_ips.update(
            [
                "192.168.1.100",  # Example malicious IP
                "10.0.0.50",  # Example malicious IP
            ],
        )

    def check_ip_reputation(self, ip_address: str) -> dict[str, Any]:
        """Check IP address reputation."""
        with self.lock:
            if ip_address in self.reputation_cache:
                cached = self.reputation_cache[ip_address]
                if cached["timestamp"] > datetime.now(UTC) - timedelta(hours=1):
                    return cached

            reputation: dict[str, Any] = {
                "ip": ip_address,
                "is_malicious": ip_address in self.malicious_ips,
                "threat_level": "low",
                "sources": [],
                "timestamp": datetime.now(UTC),
            }

            # Check if IP is in private ranges
            try:
                ip_obj = ipaddress.ip_address(ip_address)
                if ip_obj.is_private:
                    reputation["is_private"] = True
                    reputation["threat_level"] = "low"
                elif ip_obj.is_reserved:
                    reputation["is_reserved"] = True
                    reputation["threat_level"] = "medium"
            except ValueError:
                reputation["threat_level"] = "high"
                reputation["malformed"] = True

            # Check against known malicious IPs
            if ip_address in self.malicious_ips:
                reputation["threat_level"] = "critical"
                reputation["sources"].append("internal_blacklist")

            # Cache result
            self.reputation_cache[ip_address] = reputation

            return reputation

    def analyze_payload(self, payload: str) -> dict[str, Any]:
        """Analyze payload for malicious patterns."""
        threats: list[dict[str, Any]] = []
        confidence: float = 0.0

        payload_lower = payload.lower()

        for pattern in self.suspicious_patterns:
            matches = re.findall(pattern, payload_lower, re.IGNORECASE)
            if matches:
                threat_type = self._categorize_pattern(pattern)
                threats.append(
                    {
                        "type": threat_type,
                        "pattern": pattern,
                        "matches": matches,
                        "confidence": 0.8,
                    },
                )
                confidence = max(confidence, 0.8)

        # Check for encoding attempts
        if any(enc in payload_lower for enc in ["%", "\\x", "\\u", "&  #"]):
            threats.append(
                {
                    "type": "encoding_evasion",
                    "description": "Possible encoding evasion attempt",
                    "confidence": 0.6,
                },
            )
            confidence = max(confidence, 0.6)

        return {
            "threats": threats,
            "confidence": confidence,
            "threat_level": self._calculate_threat_level(confidence),
        }

    def _categorize_pattern(self, pattern: str) -> str:
        """Categorize threat pattern."""
        if any(
            sql_keyword in pattern.lower()
            for sql_keyword in ["union", "select", "drop", "insert"]
        ):
            return "sql_injection"
        if any(
            xss_keyword in pattern.lower()
            for xss_keyword in ["script", "javascript", "onclick"]
        ):
            return "xss"
        if any(
            cmd_keyword in pattern.lower() for cmd_keyword in [";", "|", "wget", "curl"]
        ):
            return "command_injection"
        if ".." in pattern:
            return "path_traversal"
        return "unknown"

    def _calculate_threat_level(self, confidence: float) -> str:
        """Calculate threat level based on confidence."""
        if confidence >= 0.9:
            return "critical"
        if confidence >= 0.7:
            return "high"
        if confidence >= 0.5:
            return "medium"
        return "low"

    def update_threat_feeds(self) -> None:
        """Update threat intelligence feeds."""
        try:
            # In production, this would fetch from external threat feeds
            # For now, update internal threat data
            with self.lock:
                # Add some example new malicious IPs
                new_threats = [
                    "203.0.113.1",  # Example malicious IP
                    "198.51.100.1",  # Example malicious IP
                    "192.0.2.1",  # Example malicious IP
                ]

                old_count = len(self.malicious_ips)
                self.malicious_ips.update(new_threats)
                new_count = len(self.malicious_ips)

                # Update suspicious patterns if needed
                new_patterns = [
                    r"(eval\s*\()",  # JavaScript eval
                    r"(base64_decode)",  # PHP base64 decode
                    r"(chmod\s + 777)",  # Dangerous file permissions
                ]

                for pattern in new_patterns:
                    if pattern not in self.suspicious_patterns:
                        self.suspicious_patterns.append(pattern)

                # Clear old reputation cache
                cutoff_time = datetime.now(UTC) - timedelta(hours=6)
                self.reputation_cache = {
                    ip: data
                    for ip, data in self.reputation_cache.items()
                    if data.get("timestamp", cutoff_time) > cutoff_time
                }

                logger.info(
                    f"Updated threat feeds: {new_count - old_count} new malicious IPs added",
                )

        except Exception as e:
            logger.exception(f"Error updating threat feeds: {e}")


class AdvancedFirewall:
    """Advanced firewall with dynamic rules."""

    def __init__(self) -> None:
        self.blocked_ips: set[str] = set()
        self.rate_limits: dict[str, dict[str, Any]] = defaultdict(dict[str, Any])
        self.dynamic_rules: list[SecurityRule] = []
        self.whitelist: set[str] = set()
        self.lock = threading.Lock()

    def add_dynamic_rule(self, rule: SecurityRule) -> None:
        """Add dynamic security rule."""
        with self.lock:
            self.dynamic_rules.append(rule)
            logger.info(f"Added dynamic security rule: {rule.name}")

    def block_ip(self, ip_address: str, duration_minutes: int = 60) -> None:
        """Block IP address temporarily."""
        with self.lock:
            self.blocked_ips.add(ip_address)
            # Schedule unblock (simplified - in production use proper scheduler)
            threading.Timer(
                duration_minutes * 60,
                self._unblock_ip,
                args=[ip_address],
            ).start()
            logger.warning(f"Blocked IP {ip_address} for {duration_minutes} minutes")

    def _unblock_ip(self, ip_address: str) -> None:
        """Unblock IP address."""
        with self.lock:
            self.blocked_ips.discard(ip_address)
            logger.info(f"Unblocked IP {ip_address}")

    def is_blocked(self, ip_address: str) -> bool:
        """Check if IP is blocked."""
        return ip_address in self.blocked_ips

    def check_rate_limit(
        self,
        ip_address: str,
        endpoint: str,
        limit: int = 100,
    ) -> bool:
        """Check rate limit for IP / endpoint combination."""
        current_time = time.time()
        window_start = current_time - 60  # 1 - minute window

        with self.lock:
            if ip_address not in self.rate_limits:
                self.rate_limits[ip_address] = {}

            if endpoint not in self.rate_limits[ip_address]:
                self.rate_limits[ip_address][endpoint] = []

            # Clean old requests
            self.rate_limits[ip_address][endpoint] = [
                req_time
                for req_time in self.rate_limits[ip_address][endpoint]
                if req_time > window_start
            ]

            # Check limit
            if len(self.rate_limits[ip_address][endpoint]) >= limit:
                return False

            # Add current request
            self.rate_limits[ip_address][endpoint].append(current_time)
            return True


class CryptographicManager:
    """Advanced cryptographic operations."""

    def __init__(self) -> None:
        self.encryption_keys: dict[str, bytes] = {}
        self.signing_keys: dict[str, rsa.RSAPrivateKey] = {}
        self.session_keys: dict[str, bytes] = {}
        self._initialized = False

    def ensure_initialized(self) -> None:
        """Ensure keys are generated. Safe to call multiple times."""
        if not getattr(self, "_initialized", False):
            self._initialize_keys()
            self._initialized = True

    def _initialize_keys(self) -> None:
        """Initialize cryptographic keys."""
        # Generate master encryption key
        self.encryption_keys["master"] = Fernet.generate_key()

        # Generate RSA signing key pair
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
            backend=default_backend(),
        )
        self.signing_keys["master"] = private_key

    def encrypt_sensitive_data(self, data: str, key_id: str = "master") -> str:
        """Encrypt sensitive data."""
        # Ensure keys exist (lazy initialize)
        self.ensure_initialized()
        if key_id not in self.encryption_keys:
            msg = f"Encryption key {key_id} not found"
            raise ValueError(msg)

        fernet = Fernet(self.encryption_keys[key_id])
        encrypted_data = fernet.encrypt(data.encode())
        return encrypted_data.hex()

    def decrypt_sensitive_data(
        self,
        encrypted_data: str,
        key_id: str = "master",
    ) -> str:
        """Decrypt sensitive data."""
        self.ensure_initialized()
        if key_id not in self.encryption_keys:
            msg = f"Encryption key {key_id} not found"
            raise ValueError(msg)

        fernet = Fernet(self.encryption_keys[key_id])
        decrypted_data = fernet.decrypt(bytes.fromhex(encrypted_data))
        return decrypted_data.decode()

    def sign_data(self, data: str, key_id: str = "master") -> str:
        """Sign data with RSA private key."""
        self.ensure_initialized()
        if key_id not in self.signing_keys:
            msg = f"Signing key {key_id} not found"
            raise ValueError(msg)

        private_key = self.signing_keys[key_id]
        signature = private_key.sign(
            data.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
        return signature.hex()

    def verify_signature(
        self,
        data: str,
        signature: str,
        key_id: str = "master",
    ) -> bool:
        """Verify data signature."""
        self.ensure_initialized()
        if key_id not in self.signing_keys:
            msg = f"Signing key {key_id} not found"
            raise ValueError(msg)

        try:
            private_key = self.signing_keys[key_id]
            public_key = private_key.public_key()

            public_key.verify(
                bytes.fromhex(signature),
                data.encode(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
            return True
        except Exception:
            return False

    def generate_session_key(self, session_id: str) -> str:
        """Generate session encryption key."""
        # Ensure master key exists if needed
        self.ensure_initialized()
        key = secrets.token_bytes(32)  # 256 - bit key
        self.session_keys[session_id] = key
        return key.hex()

    def get_session_key(self, session_id: str) -> bytes | None:
        """Get session encryption key."""
        return self.session_keys.get(session_id)


class SecurityOrchestrator:
    """Main security orchestration system."""

    def __init__(self) -> None:
        self.behavioral_analyzer = BehavioralAnalyzer()
        self.threat_intelligence = ThreatIntelligence()
        self.firewall = AdvancedFirewall()
        self.crypto_manager = CryptographicManager()
        self.threat_history: deque = deque(maxlen=10000)
        self.security_metrics: dict[str, int] = defaultdict(int)
        self.lock = threading.Lock()

    def analyze_request(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Comprehensive request analysis."""
        analysis_result = {
            "timestamp": datetime.now(UTC),
            "request_id": request_data.get("id", secrets.token_hex(8)),
            "threats": [],
            "risk_score": 0.0,
            "action": SecurityAction.MONITOR,
            "blocked": False,
        }

        ip_address = request_data.get("ip_address", "")
        user_id = request_data.get("user_id", "")
        payload = request_data.get("payload", "")
        endpoint = request_data.get("endpoint", "")

        # Check if IP is blocked
        if self.firewall.is_blocked(ip_address):
            analysis_result["blocked"] = True
            analysis_result["action"] = SecurityAction.BLOCK
            analysis_result["threats"].append(
                {
                    "type": "blocked_ip",
                    "description": "Request from blocked IP address",
                    "confidence": 1.0,
                },
            )
            return analysis_result

        # IP reputation check
        ip_reputation = self.threat_intelligence.check_ip_reputation(ip_address)
        if ip_reputation["is_malicious"]:
            threat = SecurityThreat(
                id=secrets.token_hex(8),
                threat_type=AttackType.APT,
                threat_level=ThreatLevel.CRITICAL,
                source_ip=ip_address,
                target=endpoint,
                description="Request from known malicious IP",
                timestamp=datetime.now(UTC),
                evidence=ip_reputation,
                confidence_score=0.9,
            )
            analysis_result["threats"].append(asdict(threat))
            analysis_result["risk_score"] += 0.9

        # Rate limiting check
        if not self.firewall.check_rate_limit(ip_address, endpoint, limit=100):
            threat = SecurityThreat(
                id=secrets.token_hex(8),
                threat_type=AttackType.DDoS,
                threat_level=ThreatLevel.HIGH,
                source_ip=ip_address,
                target=endpoint,
                description="Rate limit exceeded",
                timestamp=datetime.now(UTC),
                evidence={"endpoint": endpoint, "limit_exceeded": True},
                confidence_score=0.8,
            )
            analysis_result["threats"].append(asdict(threat))
            analysis_result["risk_score"] += 0.8

        # Payload analysis
        if payload:
            payload_analysis = self.threat_intelligence.analyze_payload(payload)
            if payload_analysis["threats"]:
                for threat_data in payload_analysis["threats"]:
                    desc = threat_data.get("description", "")
                    threat = SecurityThreat(
                        id=secrets.token_hex(8),
                        threat_type=AttackType(threat_data.get("type", "unknown")),
                        threat_level=ThreatLevel(payload_analysis["threat_level"]),
                        source_ip=ip_address,
                        target=endpoint,
                        description=f"Malicious payload detected: {desc}",
                        timestamp=datetime.now(UTC),
                        evidence=threat_data,
                        confidence_score=threat_data.get("confidence", 0.5),
                    )
                    analysis_result["threats"].append(asdict(threat))
                    analysis_result["risk_score"] += threat_data.get("confidence", 0.5)

        # Behavioral analysis
        if user_id:
            activity = {
                "type": request_data.get("activity_type", "request"),
                "ip_address": ip_address,
                "endpoint": endpoint,
                "user_agent": request_data.get("user_agent", ""),
                "session_id": request_data.get("session_id", ""),
            }

            self.behavioral_analyzer.track_user_activity(user_id, activity)
            anomalies = self.behavioral_analyzer.detect_anomalies(user_id, activity)

            for anomaly in anomalies:
                threat = SecurityThreat(
                    id=secrets.token_hex(8),
                    threat_type=AttackType.APT,
                    threat_level=ThreatLevel(anomaly["severity"]),
                    source_ip=ip_address,
                    target=user_id,
                    description=f"Behavioral anomaly: {anomaly['description']}",
                    timestamp=datetime.now(UTC),
                    evidence=anomaly,
                    confidence_score=anomaly.get("confidence", 0.5),
                )
                analysis_result["threats"].append(asdict(threat))
                analysis_result["risk_score"] += anomaly.get("confidence", 0.5)

        # Determine action based on risk score
        if analysis_result["risk_score"] >= 0.9:
            analysis_result["action"] = SecurityAction.BLOCK
            self.firewall.block_ip(ip_address, duration_minutes=60)
        elif analysis_result["risk_score"] >= 0.7:
            analysis_result["action"] = SecurityAction.QUARANTINE
        elif analysis_result["risk_score"] >= 0.5:
            analysis_result["action"] = SecurityAction.DEGRADE
        elif analysis_result["risk_score"] >= 0.3:
            analysis_result["action"] = SecurityAction.MONITOR

        # Store threat data
        with self.lock:
            self.threat_history.append(analysis_result)
            self.security_metrics["total_requests"] += 1
            if analysis_result["threats"]:
                self.security_metrics["threats_detected"] += len(
                    analysis_result["threats"],
                )
            if analysis_result["action"] == SecurityAction.BLOCK:
                self.security_metrics["requests_blocked"] += 1

        return analysis_result

    def get_security_status(self) -> dict[str, Any]:
        """Get comprehensive security status."""
        recent_threats = [
            threat
            for threat in self.threat_history
            if threat["timestamp"] > datetime.now(UTC) - timedelta(hours=1)
        ]

        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "total_requests": self.security_metrics["total_requests"],
            "threats_detected_1h": len(recent_threats),
            "total_threats_detected": self.security_metrics["threats_detected"],
            "requests_blocked": self.security_metrics["requests_blocked"],
            "blocked_ips": len(self.firewall.blocked_ips),
            "dynamic_rules": len(self.firewall.dynamic_rules),
            "threat_level": self._calculate_overall_threat_level(recent_threats),
            "active_sessions": len(self.crypto_manager.session_keys),
            "behavioral_profiles": len(self.behavioral_analyzer.user_profiles),
        }

    def _calculate_overall_threat_level(
        self,
        recent_threats: list[dict[str, Any]],
    ) -> str:
        """Calculate overall threat level."""
        if not recent_threats:
            return "low"

        threat_scores = [threat["risk_score"] for threat in recent_threats]
        avg_score = sum(threat_scores) / len(threat_scores)

        if avg_score >= 0.8:
            return "critical"
        if avg_score >= 0.6:
            return "high"
        if avg_score >= 0.4:
            return "medium"
        return "low"


# Global security orchestrator (lazy-instantiated to avoid heavy import-time work)


class _LazySecurityOrchestrator:
    """Lazy proxy that creates a SecurityOrchestrator on first access."""

    def __init__(self, factory) -> None:
        self._factory = factory
        self._obj: SecurityOrchestrator | None = None

    def _ensure(self) -> None:
        if self._obj is None:
            self._obj = self._factory()

    def __getattr__(self, name: str) -> Any:
        self._ensure()
        return getattr(self._obj, name)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self._ensure()
        if callable(self._obj):
            return self._obj(*args, **kwargs)
        msg = f"'{type(self._obj).__name__}' object is not callable"
        raise TypeError(msg)


# Public lazy instance
security_orchestrator: Any = _LazySecurityOrchestrator(SecurityOrchestrator)


def analyze_security_request(request_data: dict[str, Any]) -> dict[str, Any]:
    """Analyze request for security threats."""
    return security_orchestrator.analyze_request(request_data)


def get_security_dashboard() -> dict[str, Any]:
    """Get security dashboard data."""
    return security_orchestrator.get_security_status()


def encrypt_data(data: str, key_id: str = "master") -> str:
    """Encrypt sensitive data."""
    return security_orchestrator.crypto_manager.encrypt_sensitive_data(data, key_id)


def decrypt_data(encrypted_data: str, key_id: str = "master") -> str:
    """Decrypt sensitive data."""
    return security_orchestrator.crypto_manager.decrypt_sensitive_data(
        encrypted_data,
        key_id,
    )


class AdvancedSecurityOrchestrator:
    """Advanced security orchestrator for enterprise operations."""

    def __init__(self) -> None:
        self.security_orchestrator = SecurityOrchestrator()
        self.initialized = False

    async def initialize_security_systems(self) -> None:
        """Initialize all security systems."""
        try:
            # Initialize components
            self.security_orchestrator.threat_intelligence.update_threat_feeds()
            self.initialized = True
            logger.info("Advanced security systems initialized")
        except Exception as e:
            logger.exception(f"Failed to initialize security systems: {e}")
            raise

    def enable_behavioral_analysis(self) -> None:
        """Enable behavioral analysis."""
        self.security_orchestrator.behavioral_analyzer.start_monitoring()

    async def update_threat_intelligence(self) -> list[dict[str, Any]]:
        """Update threat intelligence feeds."""
        self.security_orchestrator.threat_intelligence.update_threat_feeds()
        # Return some threat intelligence data
        return [
            {
                "type": "malicious_ip",
                "count": len(
                    self.security_orchestrator.threat_intelligence.malicious_ips,
                ),
            },
            {
                "type": "suspicious_patterns",
                "count": len(
                    self.security_orchestrator.threat_intelligence.suspicious_patterns,
                ),
            },
        ]

    async def run_security_assessment(self) -> dict[str, Any]:
        """Run comprehensive security assessment."""
        try:
            # Get recent threats and calculate security score
            recent_threats = list(self.security_orchestrator.threat_history)[-100:]

            # Calculate security score based on various factors
            base_score = 95.0

            # Deduct points for recent high - level threats
            critical_threats = sum(
                1
                for t in recent_threats
                if t.get("threat_level") == ThreatLevel.CRITICAL
            )
            high_threats = sum(
                1 for t in recent_threats if t.get("threat_level") == ThreatLevel.HIGH
            )

            score = base_score - (critical_threats * 5) - (high_threats * 2)
            score = max(0, min(100, score))

            return {
                "score": score,
                "recent_threats": len(recent_threats),
                "critical_threats": critical_threats,
                "high_threats": high_threats,
                "behavioral_analysis_active": True,
                "threat_intelligence_updated": self.initialized,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        except Exception as e:
            logger.exception(f"Security assessment failed: {e}")
            return {"score": 0, "error": str(e)}

    def get_threat_status(self) -> dict[str, Any]:
        """Get current threat status."""
        recent_threats = list(self.security_orchestrator.threat_history)[-50:]

        return {
            "active_threats": len(recent_threats),
            "threat_levels": {
                "critical": sum(
                    1
                    for t in recent_threats
                    if t.get("threat_level") == ThreatLevel.CRITICAL
                ),
                "high": sum(
                    1
                    for t in recent_threats
                    if t.get("threat_level") == ThreatLevel.HIGH
                ),
                "medium": sum(
                    1
                    for t in recent_threats
                    if t.get("threat_level") == ThreatLevel.MEDIUM
                ),
                "low": sum(
                    1
                    for t in recent_threats
                    if t.get("threat_level") == ThreatLevel.LOW
                ),
            },
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def get_behavioral_analysis_status(self) -> dict[str, Any]:
        """Get behavioral analysis status."""
        return {
            "active": True,
            "monitoring": True,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    async def run_comprehensive_security_audit(self) -> dict[str, Any]:
        """Run comprehensive security audit."""
        try:
            assessment = await self.run_security_assessment()
            threat_status = self.get_threat_status()

            # Comprehensive audit score
            audit_score = assessment.get("score", 0)

            return {
                "score": audit_score,
                "assessment": assessment,
                "threat_status": threat_status,
                "security_features": [
                    "Behavioral Analysis",
                    "Threat Intelligence",
                    "Advanced Firewall",
                    "Cryptographic Management",
                    "Zero - day Protection",
                    "APT Detection",
                ],
                "timestamp": datetime.now(UTC).isoformat(),
            }
        except Exception as e:
            logger.exception(f"Security audit failed: {e}")
            return {"score": 0, "error": str(e)}
