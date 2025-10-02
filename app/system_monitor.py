# app / system_monitor.py
"""
Advanced system monitoring for admin dashboard with real - time metrics,
    health checks, and professional charts.
"""

import asyncio
import logging
import sqlite3
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, cast

from app._typing_shims import ISyncConnection

if TYPE_CHECKING:
    # For static checking declare a forward reference for BlockUserRequest
    from typing import TYPE_CHECKING as _T  # noqa: F401

    import psutil  # pragma: no cover
else:
    try:
        import psutil
    except Exception:
        psutil = None  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """System performance metrics."""

    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_available_gb: float
    disk_usage_percent: float
    disk_free_gb: float
    network_bytes_sent: int
    network_bytes_recv: int
    active_connections: int
    uptime_seconds: int


@dataclass
class ApplicationMetrics:
    """Application - specific metrics."""

    timestamp: datetime
    total_users: int
    active_sessions: int
    requests_per_minute: int
    response_time_avg: float
    error_rate_percent: float
    database_connections: int
    cache_hit_rate: float


@dataclass
class SecurityMetrics:
    """Security monitoring metrics."""

    timestamp: datetime
    failed_login_attempts: int
    blocked_ips: int
    suspicious_activities: int
    threat_level: str
    last_security_scan: datetime


class SystemMonitor:
    def auto_block_suspicious_users(
        self, admin_manager, guardian_module, risk_threshold=0.9
    ):
        """Scan recent transactions, auto - block users with high risk, and log alerts."""
        try:
            import sqlite3
            from datetime import datetime, timedelta

            # Scan last 10 minutes of transactions
            cutoff = datetime.now(UTC) - timedelta(minutes=10)
            with sqlite3.connect(self.db_path) as conn:
                typed_conn = cast(ISyncConnection, conn)
                cursor = typed_conn.cursor()
                cursor.execute(
                    """
                    SELECT
                        user_email, id, memo, amount, fee, direction,
                            is_internal, tags, timestamp
                    FROM transactions
                    WHERE timestamp > ?
                    """,
                    (cutoff.isoformat(),),
                )
                rows = cursor.fetchall()
            for row in rows:
                user_email = row[0]
                tx = {
                    "memo": row[2],
                    "amount": row[3],
                    "fee": row[4],
                    "direction": row[5],
                    "is_internal": row[6],
                    "tags": row[7].split(",") if row[7] else [],
                }
                score, flags = guardian_module.score_risk(tx)
                if score >= risk_threshold:
                    # Block user if not already blocked
                    user = admin_manager.get_user_by_email(user_email)
                    if user and not user.is_blocked():
                        # Import model at runtime to avoid static attr-defined issues
                        import importlib

                        models_mod = importlib.import_module("app.models")
                        BlockUserRequestCls = getattr(models_mod, "BlockUserRequest")

                        req = BlockUserRequestCls(
                            target_email=user_email,
                            reason=f"Auto-blocked: risk={score}, flags={flags}",
                            duration_hours=None,
                        )
                        admin_manager.block_user(
                            admin_email=admin_manager.notification_email,
                            request=req,
                        )
                        self.add_alert(
                            "security",
                            "high",
                            (
                                f"Auto - blocked {user_email} for suspicious activity. "
                                f"Risk={score}, Flags={flags}"
                            ),
                        )
        except Exception as e:
            logger.error("Error in auto_block_suspicious_users: %s", e)

    """Comprehensive system monitoring for enterprise admin dashboard."""

    def __init__(self, db_path: str = "data/klerno.db", init_db: bool = False):
        """Create a SystemMonitor instance.

        By default this constructor does not perform any filesystem or
        database initialization. Pass init_db=True to create monitoring
        tables immediately (used by application startup).
        """
        self.db_path = db_path
        self.start_time = time.time()
        self.request_count = 0
        self.response_times: list[float] = []
        self.error_count = 0
        self.active_sessions: set[Any] = set()
        self.failed_logins = 0

        # Avoid side-effects during import/normal construction. Table
        # initialization is opt-in to keep tests and tooling safe; call
        # init_monitoring_tables() explicitly when needed.
        if init_db:
            self.init_monitoring_tables()

    def init_monitoring_tables(self):
        """Initialize monitoring database tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                typed_conn = cast(ISyncConnection, conn)
                cursor = typed_conn.cursor()

                # System metrics table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS system_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            cpu_percent REAL,
                            memory_percent REAL,
                            memory_available_gb REAL,
                            disk_usage_percent REAL,
                            disk_free_gb REAL,
                            network_bytes_sent INTEGER,
                            network_bytes_recv INTEGER,
                            active_connections INTEGER,
                            uptime_seconds INTEGER
                    )
                """
                )

                # Application metrics table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS app_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            total_users INTEGER,
                            active_sessions INTEGER,
                            requests_per_minute INTEGER,
                            response_time_avg REAL,
                            error_rate_percent REAL,
                            database_connections INTEGER,
                            cache_hit_rate REAL
                    )
                """
                )

                # Security metrics table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS security_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            failed_login_attempts INTEGER,
                            blocked_ips INTEGER,
                            suspicious_activities INTEGER,
                            threat_level TEXT,
                            last_security_scan TIMESTAMP
                    )
                """
                )

                # Real - time alerts table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS system_alerts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            alert_type TEXT NOT NULL,
                            severity TEXT NOT NULL,
                            message TEXT NOT NULL,
                            resolved BOOLEAN DEFAULT 0,
                            resolved_at TIMESTAMP
                    )
                """
                )

                conn.commit()
        except Exception as e:
            logger.error("Error initializing monitoring tables: %s", e)

    def get_system_metrics(self) -> SystemMetrics | None:
        """Get current system performance metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_gb = memory.available / (1024**3)

            # Disk usage
            disk = psutil.disk_usage("/")
            disk_usage_percent = (disk.used / disk.total) * 100
            disk_free_gb = disk.free / (1024**3)

            # Network stats
            network = psutil.net_io_counters()
            # psutil may return a namedtuple or None; guard attribute access
            network_bytes_sent = (
                getattr(network, "bytes_sent", 0) if network is not None else 0
            )
            network_bytes_recv = (
                getattr(network, "bytes_recv", 0) if network is not None else 0
            )

            # Connection count
            active_connections = len(psutil.net_connections())

            # Uptime
            uptime_seconds = int(time.time() - self.start_time)

            cpu_val = (
                float(cpu_percent) if isinstance(cpu_percent, (int, float)) else 0.0
            )

            return SystemMetrics(
                timestamp=datetime.now(UTC),
                cpu_percent=cpu_val,
                memory_percent=memory_percent,
                memory_available_gb=memory_available_gb,
                disk_usage_percent=disk_usage_percent,
                disk_free_gb=disk_free_gb,
                network_bytes_sent=network_bytes_sent,
                network_bytes_recv=network_bytes_recv,
                active_connections=active_connections,
                uptime_seconds=uptime_seconds,
            )
        except Exception as e:
            logger.error("Error getting system metrics: %s", e)
            return None

    def get_application_metrics(self) -> ApplicationMetrics | None:
        """Get current application metrics."""
        try:
            # Count total users
            with sqlite3.connect(self.db_path) as conn:
                typed_conn = cast(ISyncConnection, conn)
                cursor = typed_conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM users_enhanced")
                total_users = cursor.fetchone()[0]

            # Calculate requests per minute
            current_time = time.time()
            minute_ago = current_time - 60
            requests_per_minute = len(
                [t for t in self.response_times if t > minute_ago]
            )

            # Calculate average response time
            recent_times = [t for t in self.response_times if t > minute_ago]
            response_time_avg = (
                sum(recent_times) / len(recent_times) if recent_times else 0
            )

            # Calculate error rate
            total_requests = len(self.response_times)
            error_rate_percent = (
                (self.error_count / total_requests * 100) if total_requests > 0 else 0
            )

            return ApplicationMetrics(
                timestamp=datetime.now(UTC),
                total_users=total_users,
                active_sessions=len(self.active_sessions),
                requests_per_minute=requests_per_minute,
                response_time_avg=response_time_avg,
                error_rate_percent=error_rate_percent,
                database_connections=1,  # Simplified for SQLite
                cache_hit_rate=85.0,  # Placeholder - would be calculated from cache stats
            )
        except Exception as e:
            logger.error("Error getting application metrics: %s", e)
            return None

    def get_security_metrics(self) -> SecurityMetrics | None:
        """Get current security metrics."""
        try:
            # Count recent failed logins
            hour_ago = datetime.now(UTC) - timedelta(hours=1)

            with sqlite3.connect(self.db_path) as conn:
                typed_conn = cast(ISyncConnection, conn)
                cursor = typed_conn.cursor()
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM admin_actions
                    WHERE action='failed_login' AND timestamp > ?
                """,
                    (hour_ago.isoformat(),),
                )
                failed_logins_hour = cursor.fetchone()[0]

            # Determine threat level based on activity
            threat_level = "LOW"
            if failed_logins_hour > 10:
                threat_level = "MEDIUM"
            if failed_logins_hour > 50:
                threat_level = "HIGH"

            return SecurityMetrics(
                timestamp=datetime.now(UTC),
                failed_login_attempts=failed_logins_hour,
                blocked_ips=0,  # Would be calculated from firewall logs
                suspicious_activities=failed_logins_hour,
                threat_level=threat_level,
                last_security_scan=datetime.now(UTC),
            )
        except Exception as e:
            logger.error("Error getting security metrics: %s", e)
            return None

    def store_metrics(self):
        """Store current metrics in database."""
        try:
            system_metrics = self.get_system_metrics()
            app_metrics = self.get_application_metrics()
            security_metrics = self.get_security_metrics()

            with sqlite3.connect(self.db_path) as conn:
                typed_conn = cast(ISyncConnection, conn)
                cursor = typed_conn.cursor()

                if system_metrics:
                    cursor.execute(
                        """
                        INSERT INTO system_metrics
                        (cpu_percent, memory_percent, memory_available_gb,
                         disk_usage_percent, disk_free_gb, network_bytes_sent,
                             network_bytes_recv, active_connections, uptime_seconds)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            system_metrics.cpu_percent,
                            system_metrics.memory_percent,
                            system_metrics.memory_available_gb,
                            system_metrics.disk_usage_percent,
                            system_metrics.disk_free_gb,
                            system_metrics.network_bytes_sent,
                            system_metrics.network_bytes_recv,
                            system_metrics.active_connections,
                            system_metrics.uptime_seconds,
                        ),
                    )

                if app_metrics:
                    cursor.execute(
                        """
                        INSERT INTO app_metrics
                        (total_users, active_sessions, requests_per_minute,
                         response_time_avg, error_rate_percent, database_connections,
                             cache_hit_rate)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            app_metrics.total_users,
                            app_metrics.active_sessions,
                            app_metrics.requests_per_minute,
                            app_metrics.response_time_avg,
                            app_metrics.error_rate_percent,
                            app_metrics.database_connections,
                            app_metrics.cache_hit_rate,
                        ),
                    )

                if security_metrics:
                    cursor.execute(
                        """
                        INSERT INTO security_metrics
                        (failed_login_attempts, blocked_ips, suspicious_activities,
                         threat_level, last_security_scan)
                        VALUES (?, ?, ?, ?, ?)
                    """,
                        (
                            security_metrics.failed_login_attempts,
                            security_metrics.blocked_ips,
                            security_metrics.suspicious_activities,
                            security_metrics.threat_level,
                            security_metrics.last_security_scan.isoformat(),
                        ),
                    )

                conn.commit()
        except Exception as e:
            logger.error("Error storing metrics: %s", e)

    def get_dashboard_data(self, hours: int = 24) -> dict[str, Any]:
        """Get comprehensive dashboard data for admin interface."""
        try:
            cutoff_time = datetime.now(UTC) - timedelta(hours=hours)

            with sqlite3.connect(self.db_path) as conn:
                typed_conn = cast(ISyncConnection, conn)
                cursor = typed_conn.cursor()

                # Get recent system metrics
                cursor.execute(
                    """
                    SELECT * FROM system_metrics
                    WHERE timestamp > ?
                    ORDER BY timestamp DESC
                """,
                    (cutoff_time.isoformat(),),
                )
                system_data = cursor.fetchall()

                # Get recent app metrics
                cursor.execute(
                    """
                    SELECT * FROM app_metrics
                    WHERE timestamp > ?
                    ORDER BY timestamp DESC
                """,
                    (cutoff_time.isoformat(),),
                )
                app_data = cursor.fetchall()

                # Get recent security metrics
                cursor.execute(
                    """
                    SELECT * FROM security_metrics
                    WHERE timestamp > ?
                    ORDER BY timestamp DESC
                """,
                    (cutoff_time.isoformat(),),
                )
                security_data = cursor.fetchall()

                # Get active alerts
                cursor.execute(
                    """
                    SELECT * FROM system_alerts
                    WHERE resolved=0
                    ORDER BY timestamp DESC
                """
                )
                alerts = cursor.fetchall()

            # Get current status
            current_system = self.get_system_metrics()
            current_app = self.get_application_metrics()
            current_security = self.get_security_metrics()

            system_cols = [
                "id",
                "timestamp",
                "cpu_percent",
                "memory_percent",
                "memory_available_gb",
                "disk_usage_percent",
                "disk_free_gb",
                "network_bytes_sent",
                "network_bytes_recv",
                "active_connections",
                "uptime_seconds",
            ]
            app_cols = [
                "id",
                "timestamp",
                "total_users",
                "active_sessions",
                "requests_per_minute",
                "response_time_avg",
                "error_rate_percent",
                "database_connections",
                "cache_hit_rate",
            ]
            security_cols = [
                "id",
                "timestamp",
                "failed_login_attempts",
                "blocked_ips",
                "suspicious_activities",
                "threat_level",
                "last_security_scan",
            ]
            alert_cols = [
                "id",
                "timestamp",
                "alert_type",
                "severity",
                "message",
                "resolved",
                "resolved_at",
            ]

            return {
                "status": {
                    "server_online": True,
                    "database_connected": True,
                    "last_update": datetime.now(UTC).isoformat(),
                    "uptime_hours": round((time.time() - self.start_time) / 3600, 1),
                },
                "current_metrics": {
                    "system": asdict(current_system) if current_system else None,
                    "application": asdict(current_app) if current_app else None,
                    "security": asdict(current_security) if current_security else None,
                },
                "historical_data": {
                    "system": [
                        dict(zip(system_cols, row, strict=False)) for row in system_data
                    ],
                    "application": [
                        dict(zip(app_cols, row, strict=False)) for row in app_data
                    ],
                    "security": [
                        dict(zip(security_cols, row, strict=False))
                        for row in security_data
                    ],
                },
                "alerts": [
                    dict(zip(alert_cols, alert, strict=False)) for alert in alerts
                ],
            }
        except Exception as e:
            logger.error("Error getting dashboard data: %s", e)
            return {"error": str(e)}

    def add_alert(self, alert_type: str, severity: str, message: str):
        """Add system alert."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO system_alerts (alert_type, severity, message)
                    VALUES (?, ?, ?)
                """,
                    (alert_type, severity, message),
                )
                conn.commit()
        except Exception as e:
            logger.error("Error adding alert: %s", e)

    def record_request(self, response_time: float, is_error: bool = False):
        """Record API request for metrics."""
        self.request_count += 1
        self.response_times.append(time.time())
        if is_error:
            self.error_count += 1

        # Keep only last 1000 response times
        if len(self.response_times) > 1000:
            self.response_times = self.response_times[-1000:]

    def add_session(self, session_id: str):
        """Add active session."""
        self.active_sessions.add(session_id)

    def remove_session(self, session_id: str):
        """Remove active session."""
        self.active_sessions.discard(session_id)

    def record_failed_login(self):
        """Record failed login attempt."""
        self.failed_logins += 1

    async def start_monitoring(self, admin_manager=None, guardian_module=None):
        """Start background monitoring task with automated incident response."""
        while True:
            try:
                self.store_metrics()
                # Automated incident response: auto - block suspicious users
                if admin_manager and guardian_module:
                    self.auto_block_suspicious_users(admin_manager, guardian_module)
                # Check for alerts
                current_system = self.get_system_metrics()
                if current_system:
                    if current_system.cpu_percent > 90:
                        msg = f"CPU usage at {current_system.cpu_percent}%"
                        self.add_alert("system", "high", msg)
                    if current_system.memory_percent > 90:
                        msg = f"Memory usage at {current_system.memory_percent}%"
                        self.add_alert("system", "high", msg)
                    if current_system.disk_usage_percent > 85:
                        msg = f"Disk usage at {current_system.disk_usage_percent}%"
                        self.add_alert("system", "medium", msg)
                await asyncio.sleep(60)  # Update every minute
            except Exception as e:
                logger.error("Error in monitoring loop: %s", e)
                await asyncio.sleep(60)
                await asyncio.sleep(60)
