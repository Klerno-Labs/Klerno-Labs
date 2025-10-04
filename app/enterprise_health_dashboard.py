"""Klerno Labs Enterprise Health Monitoring Dashboard
Real-time monitoring dashboard with comprehensive health checks and alerting
"""

import json
import logging
import sqlite3
import statistics
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from app._typing_shims import ISyncConnection

if TYPE_CHECKING:
    import psutil  # pragma: no cover
    import requests  # pragma: no cover
else:
    try:
        import psutil
    except Exception:
        psutil = None  # type: ignore
    try:
        import requests
    except Exception:
        requests = None  # type: ignore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class HealthCheckResult:
    """Health check result"""

    service_name: str
    status: str  # healthy, degraded, unhealthy
    response_time_ms: float
    timestamp: datetime
    details: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None


@dataclass
class SystemMetrics:
    """System metrics snapshot"""

    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_io: dict[str, int]
    process_count: int
    load_average: list[float]
    uptime_seconds: float


@dataclass
class Alert:
    """System alert"""

    alert_id: str
    severity: str  # info, warning, error, critical
    title: str
    message: str
    service: str
    timestamp: datetime
    resolved: bool = False
    resolved_at: datetime | None = None


class EnterpriseHealthMonitor:
    """Comprehensive health monitoring system"""

    def __init__(self, database_path: str = "./data/klerno.db"):
        self.database_path = database_path
        self.health_checks: dict[str, Callable] = {}
        self.health_results: list[HealthCheckResult] = []
        self.system_metrics: list[SystemMetrics] = []
        self.active_alerts: list[Alert] = []
        self.alert_rules: dict[str, dict] = {}

        # Configuration
        self.check_interval = 30  # seconds
        self.metrics_retention_hours = 24
        self.alert_retention_days = 7

        # Threading
        self._running = True
        self._lock = threading.RLock()

        # Initialize database
        self._init_database()

        # Start monitoring threads
        self._health_thread = threading.Thread(
            target=self._health_check_worker,
            daemon=True,
        )
        self._metrics_thread = threading.Thread(
            target=self._metrics_worker,
            daemon=True,
        )
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_worker,
            daemon=True,
        )

        self._health_thread.start()
        self._metrics_thread.start()
        self._cleanup_thread.start()

        # Register default health checks
        self._register_default_health_checks()
        self._register_default_alert_rules()

        logger.info("[HEALTH] Enterprise health monitoring initialized")

    def _init_database(self):
        """Initialize health monitoring database"""
        try:
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)

            conn = cast("ISyncConnection", sqlite3.connect(self.database_path))
            cursor = conn.cursor()

            # Health check results table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS health_check_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    response_time_ms REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    details TEXT,
                    error_message TEXT
                )
            """,
            )

            # System metrics table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    cpu_percent REAL NOT NULL,
                    memory_percent REAL NOT NULL,
                    disk_percent REAL NOT NULL,
                    network_io TEXT,
                    process_count INTEGER NOT NULL,
                    load_average TEXT,
                    uptime_seconds REAL NOT NULL
                )
            """,
            )

            # Alerts table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id TEXT UNIQUE NOT NULL,
                    severity TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    service TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    resolved BOOLEAN DEFAULT FALSE,
                    resolved_at TEXT
                )
            """,
            )

            # Create indices for performance
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_health_timestamp ON health_check_results(timestamp)",
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON system_metrics(timestamp)",
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp)",
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_alerts_resolved ON alerts(resolved)",
            )

            conn.commit()
            conn.close()

            logger.info("[HEALTH] Database initialized")

        except Exception as e:
            logger.error(f"[HEALTH] Database initialization failed: {e}")

    def register_health_check(self, service_name: str, check_function: Callable):
        """Register a custom health check"""
        with self._lock:
            self.health_checks[service_name] = check_function
            logger.info(f"[HEALTH] Registered health check: {service_name}")

    def register_alert_rule(
        self,
        rule_name: str,
        condition: Callable,
        severity: str = "warning",
        title: str = "",
        message_template: str = "",
    ):
        """Register alert rule"""
        with self._lock:
            self.alert_rules[rule_name] = {
                "condition": condition,
                "severity": severity,
                "title": title or f"Alert: {rule_name}",
                "message_template": message_template
                or f"Alert condition triggered: {rule_name}",
            }
            logger.info(f"[HEALTH] Registered alert rule: {rule_name}")

        def create_alert_rule(
            self,
            rule_id: str,
            condition: str | Callable,
            threshold: float | None = None,
            severity: str = "warning",
            actions: list[str] | None = None,
            title: str = "",
            message_template: str = "",
        ) -> None:
            """Compatibility alias for creating alert rules from integration hub."""

            # For backward compatibility, accept simple parameters and convert to internal format
            def cond():
                return False

            condition_callable = cond
            if callable(condition):
                condition_callable = condition

            self.register_alert_rule(
                rule_id,
                condition_callable,
                severity=severity,
                title=title,
                message_template=message_template,
            )

    def _register_default_health_checks(self):
        """Register default health checks"""

        def database_health_check():
            """Check database connectivity"""
            try:
                start_time = time.time()
                conn = cast(
                    "ISyncConnection",
                    sqlite3.connect(self.database_path, timeout=5),
                )
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                conn.close()

                response_time = (time.time() - start_time) * 1000
                return HealthCheckResult(
                    service_name="database",
                    status="healthy",
                    response_time_ms=response_time,
                    timestamp=datetime.now(),
                    details={"database_path": self.database_path},
                )
            except Exception as e:
                return HealthCheckResult(
                    service_name="database",
                    status="unhealthy",
                    response_time_ms=0,
                    timestamp=datetime.now(),
                    error_message=str(e),
                )

        def memory_health_check():
            """Check memory usage"""
            try:
                memory = psutil.virtual_memory()
                status = "healthy"

                if memory.percent > 90:
                    status = "unhealthy"
                elif memory.percent > 80:
                    status = "degraded"

                return HealthCheckResult(
                    service_name="memory",
                    status=status,
                    response_time_ms=1,
                    timestamp=datetime.now(),
                    details={
                        "percent_used": memory.percent,
                        "total_gb": round(memory.total / (1024**3), 2),
                        "available_gb": round(memory.available / (1024**3), 2),
                    },
                )
            except Exception as e:
                return HealthCheckResult(
                    service_name="memory",
                    status="unhealthy",
                    response_time_ms=0,
                    timestamp=datetime.now(),
                    error_message=str(e),
                )

        def disk_health_check():
            """Check disk usage"""
            try:
                disk = psutil.disk_usage("/")
                percent_used = (disk.used / disk.total) * 100

                status = "healthy"
                if percent_used > 95:
                    status = "unhealthy"
                elif percent_used > 85:
                    status = "degraded"

                return HealthCheckResult(
                    service_name="disk",
                    status=status,
                    response_time_ms=1,
                    timestamp=datetime.now(),
                    details={
                        "percent_used": round(percent_used, 2),
                        "total_gb": round(disk.total / (1024**3), 2),
                        "free_gb": round(disk.free / (1024**3), 2),
                    },
                )
            except Exception as e:
                return HealthCheckResult(
                    service_name="disk",
                    status="unhealthy",
                    response_time_ms=0,
                    timestamp=datetime.now(),
                    error_message=str(e),
                )

        def api_health_check():
            """Check API endpoint"""
            try:
                start_time = time.time()

                # Try to connect to local health endpoint
                try:
                    response = requests.get("http://localhost:8000/healthz", timeout=5)
                    response_time = (time.time() - start_time) * 1000

                    status = "healthy" if response.status_code == 200 else "degraded"

                    return HealthCheckResult(
                        service_name="api",
                        status=status,
                        response_time_ms=response_time,
                        timestamp=datetime.now(),
                        details={
                            "status_code": response.status_code,
                            "endpoint": "http://localhost:8000/healthz",
                        },
                    )
                except requests.exceptions.ConnectionError:
                    # API might not be running, which is ok for monitoring
                    return HealthCheckResult(
                        service_name="api",
                        status="degraded",
                        response_time_ms=0,
                        timestamp=datetime.now(),
                        details={"status": "service_unavailable"},
                    )

            except Exception as e:
                return HealthCheckResult(
                    service_name="api",
                    status="unhealthy",
                    response_time_ms=0,
                    timestamp=datetime.now(),
                    error_message=str(e),
                )

        # Register default checks
        self.register_health_check("database", database_health_check)
        self.register_health_check("memory", memory_health_check)
        self.register_health_check("disk", disk_health_check)
        self.register_health_check("api", api_health_check)

    def _register_default_alert_rules(self):
        """Register default alert rules"""

        def high_cpu_condition(metrics):
            recent_metrics = [
                m
                for m in metrics
                if (datetime.now() - m.timestamp).total_seconds() < 300
            ]
            if len(recent_metrics) >= 3:
                avg_cpu = statistics.mean([m.cpu_percent for m in recent_metrics])
                return avg_cpu > 90
            return False

        def high_memory_condition(metrics):
            recent_metrics = [
                m
                for m in metrics
                if (datetime.now() - m.timestamp).total_seconds() < 300
            ]
            if len(recent_metrics) >= 3:
                avg_memory = statistics.mean([m.memory_percent for m in recent_metrics])
                return avg_memory > 90
            return False

        def service_down_condition(health_results):
            recent_results = [
                r
                for r in health_results
                if (datetime.now() - r.timestamp).total_seconds() < 180
            ]

            service_status: dict[str, list[str]] = {}

            for result in recent_results:
                if result.service_name not in service_status:
                    service_status[result.service_name] = []
                service_status[result.service_name].append(result.status)

            for _service, statuses in service_status.items():
                if len(statuses) >= 2 and all(s == "unhealthy" for s in statuses[-2:]):
                    return True
            return False

        self.register_alert_rule(
            "high_cpu_usage",
            lambda: high_cpu_condition(self.system_metrics),
            "warning",
            "High CPU Usage",
            "CPU usage has been above 90% for the last 5 minutes",
        )

        self.register_alert_rule(
            "high_memory_usage",
            lambda: high_memory_condition(self.system_metrics),
            "error",
            "High Memory Usage",
            "Memory usage has been above 90% for the last 5 minutes",
        )

        self.register_alert_rule(
            "service_unhealthy",
            lambda: service_down_condition(self.health_results),
            "critical",
            "Service Unhealthy",
            "One or more services are reporting unhealthy status",
        )

    def _health_check_worker(self):
        """Background health check worker"""
        while self._running:
            try:
                self._run_health_checks()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"[HEALTH] Health check worker error: {e}")
                time.sleep(self.check_interval)

    def _run_health_checks(self):
        """Run all registered health checks"""
        with self._lock:
            for service_name, check_function in self.health_checks.items():
                try:
                    result = check_function()
                    self.health_results.append(result)

                    # Store in database
                    self._store_health_result(result)

                    # Log result
                    if result.status == "healthy":
                        logger.debug(
                            f"[HEALTH] {service_name}: {result.status} "
                            f"({result.response_time_ms:.1f}ms)",
                        )
                    else:
                        logger.warning(
                            f"[HEALTH] {service_name}: {result.status} - {result.error_message}",
                        )

                except Exception as e:
                    logger.error(
                        f"[HEALTH] Health check failed for {service_name}: {e}",
                    )

    def _store_health_result(self, result: HealthCheckResult):
        """Store health check result in database"""
        try:
            conn = cast("ISyncConnection", sqlite3.connect(self.database_path))
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO health_check_results
                (service_name, status, response_time_ms, timestamp, details, error_message)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    result.service_name,
                    result.status,
                    result.response_time_ms,
                    result.timestamp.isoformat(),
                    json.dumps(result.details),
                    result.error_message,
                ),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"[HEALTH] Failed to store health result: {e}")

    def _metrics_worker(self):
        """Background system metrics worker"""
        while self._running:
            try:
                self._collect_system_metrics()
                time.sleep(30)  # Collect metrics every 30 seconds
            except Exception as e:
                logger.error(f"[HEALTH] Metrics worker error: {e}")
                time.sleep(30)

    def _collect_system_metrics(self):
        """Collect system metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            # Ensure cpu_percent is a float. psutil.cpu_percent can (rarely) be
            # a list when called with percpu=True in other contexts; coerce
            # defensively so the type-checker and consumers see a float.
            # Only call float() on atomic values; if cpu_percent is a list/tuple,
            # extract the first element. This keeps the type-checker happy.
            if isinstance(cpu_percent, (list, tuple)):
                if cpu_percent:
                    first = cpu_percent[0]
                    try:
                        cpu_percent = float(first)
                    except Exception:
                        cpu_percent = 0.0
                else:
                    cpu_percent = 0.0
            else:
                try:
                    cpu_percent = float(cpu_percent)
                except Exception:
                    cpu_percent = 0.0

            # Memory usage
            memory = psutil.virtual_memory()

            # Disk usage
            disk = psutil.disk_usage("/")
            disk_percent = (disk.used / disk.total) * 100

            # Network IO
            network = psutil.net_io_counters()

            # Helper to safely extract network attributes when `network` might
            # be None or a dict-like object (common in tests / mocks).
            def _safe_net_val(net, attr: str) -> int:
                if net is None:
                    return 0
                # dict-like mock
                if isinstance(net, dict):
                    val = net.get(attr, 0)
                else:
                    val = getattr(net, attr, 0)

                # Coerce to int with fallbacks
                try:
                    return int(val)
                except Exception:
                    try:
                        return int(float(val))
                    except Exception:
                        return 0

            network_io = {
                "bytes_sent": _safe_net_val(network, "bytes_sent"),
                "bytes_recv": _safe_net_val(network, "bytes_recv"),
                "packets_sent": _safe_net_val(network, "packets_sent"),
                "packets_recv": _safe_net_val(network, "packets_recv"),
            }

            # Process count
            process_count = len(psutil.pids())

            # Load average (Unix only)
            try:
                load_average = list(psutil.getloadavg())
            except Exception:
                load_average = [0.0, 0.0, 0.0]

            # System uptime
            uptime_seconds = time.time() - psutil.boot_time()

            metrics = SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_percent=disk_percent,
                network_io=network_io,
                process_count=process_count,
                load_average=load_average,
                uptime_seconds=uptime_seconds,
            )

            with self._lock:
                self.system_metrics.append(metrics)

                # Store in database
                self._store_system_metrics(metrics)

                # Check alert rules
                self._check_alert_rules()

        except Exception as e:
            logger.error(f"[HEALTH] Failed to collect system metrics: {e}")

    def _store_system_metrics(self, metrics: SystemMetrics):
        """Store system metrics in database"""
        try:
            conn = cast("ISyncConnection", sqlite3.connect(self.database_path))
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO system_metrics
                (timestamp, cpu_percent, memory_percent, disk_percent, network_io,
                 process_count, load_average, uptime_seconds)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    metrics.timestamp.isoformat(),
                    metrics.cpu_percent,
                    metrics.memory_percent,
                    metrics.disk_percent,
                    json.dumps(metrics.network_io),
                    metrics.process_count,
                    json.dumps(metrics.load_average),
                    metrics.uptime_seconds,
                ),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"[HEALTH] Failed to store system metrics: {e}")

    def _check_alert_rules(self):
        """Check all alert rules and trigger alerts"""
        for rule_name, rule_config in self.alert_rules.items():
            try:
                condition_met = rule_config["condition"]()

                if condition_met:
                    # Check if we already have an active alert for this rule
                    existing_alert = None
                    for alert in self.active_alerts:
                        if alert.service == rule_name and not alert.resolved:
                            existing_alert = alert
                            break

                    if not existing_alert:
                        # Create new alert
                        alert = Alert(
                            alert_id=f"{rule_name}_{int(time.time())}",
                            severity=rule_config["severity"],
                            title=rule_config["title"],
                            message=rule_config["message_template"],
                            service=rule_name,
                            timestamp=datetime.now(),
                        )

                        self.active_alerts.append(alert)
                        self._store_alert(alert)

                        logger.warning(
                            f"[HEALTH] ALERT: {alert.title} - {alert.message}",
                        )

            except Exception as e:
                logger.error(f"[HEALTH] Alert rule check failed for {rule_name}: {e}")

    def _store_alert(self, alert: Alert):
        """Store alert in database"""
        try:
            conn = cast("ISyncConnection", sqlite3.connect(self.database_path))
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO alerts
                (alert_id, severity, title, message, service, timestamp, resolved, resolved_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    alert.alert_id,
                    alert.severity,
                    alert.title,
                    alert.message,
                    alert.service,
                    alert.timestamp.isoformat(),
                    alert.resolved,
                    alert.resolved_at.isoformat() if alert.resolved_at else None,
                ),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"[HEALTH] Failed to store alert: {e}")

    def _cleanup_worker(self):
        """Background cleanup worker"""
        while self._running:
            try:
                self._cleanup_old_data()
                time.sleep(3600)  # Run cleanup every hour
            except Exception as e:
                logger.error(f"[HEALTH] Cleanup worker error: {e}")
                time.sleep(3600)

    def _cleanup_old_data(self):
        """Clean up old monitoring data"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=self.metrics_retention_hours)
            alert_cutoff = datetime.now() - timedelta(days=self.alert_retention_days)

            conn = cast("ISyncConnection", sqlite3.connect(self.database_path))
            cursor = conn.cursor()

            # Clean old health results
            cursor.execute(
                "DELETE FROM health_check_results WHERE timestamp < ?",
                (cutoff_time.isoformat(),),
            )

            # Clean old system metrics
            cursor.execute(
                "DELETE FROM system_metrics WHERE timestamp < ?",
                (cutoff_time.isoformat(),),
            )

            # Clean old resolved alerts
            cursor.execute(
                "DELETE FROM alerts WHERE resolved = 1 AND timestamp < ?",
                (alert_cutoff.isoformat(),),
            )

            conn.commit()
            conn.close()

            # Clean in-memory data
            with self._lock:
                self.health_results = [
                    r for r in self.health_results if r.timestamp >= cutoff_time
                ]

                self.system_metrics = [
                    m for m in self.system_metrics if m.timestamp >= cutoff_time
                ]

                self.active_alerts = [
                    a
                    for a in self.active_alerts
                    if not a.resolved or a.timestamp >= alert_cutoff
                ]

            logger.info("[HEALTH] Old monitoring data cleaned up")

        except Exception as e:
            logger.error(f"[HEALTH] Cleanup failed: {e}")

    def get_dashboard_data(self) -> dict[str, Any]:
        """Get comprehensive dashboard data"""
        with self._lock:
            # Latest health status
            latest_health = {}
            for service_name in self.health_checks:
                service_results = [
                    r for r in self.health_results if r.service_name == service_name
                ]
                if service_results:
                    latest = max(service_results, key=lambda x: x.timestamp)
                    latest_health[service_name] = {
                        "status": latest.status,
                        "response_time_ms": latest.response_time_ms,
                        "timestamp": latest.timestamp.isoformat(),
                        "details": latest.details,
                        "error_message": latest.error_message,
                    }

            # Recent system metrics
            recent_metrics = [
                m
                for m in self.system_metrics
                if (datetime.now() - m.timestamp).total_seconds() < 3600  # Last hour
            ]

            # Active alerts
            active_alerts = [
                {
                    "alert_id": a.alert_id,
                    "severity": a.severity,
                    "title": a.title,
                    "message": a.message,
                    "service": a.service,
                    "timestamp": a.timestamp.isoformat(),
                }
                for a in self.active_alerts
                if not a.resolved
            ]

            # System summary
            if recent_metrics:
                latest_metrics = recent_metrics[-1]
                system_summary = {
                    "cpu_percent": latest_metrics.cpu_percent,
                    "memory_percent": latest_metrics.memory_percent,
                    "disk_percent": latest_metrics.disk_percent,
                    "process_count": latest_metrics.process_count,
                    "uptime_hours": latest_metrics.uptime_seconds / 3600,
                }
            else:
                system_summary = {}

            # Performance trends
            performance_trends = {}
            if len(recent_metrics) > 1:
                performance_trends = {
                    "cpu_trend": [m.cpu_percent for m in recent_metrics[-20:]],
                    "memory_trend": [m.memory_percent for m in recent_metrics[-20:]],
                    "timestamps": [
                        m.timestamp.isoformat() for m in recent_metrics[-20:]
                    ],
                }

            return {
                "timestamp": datetime.now().isoformat(),
                "overall_status": self._calculate_overall_status(),
                "health_checks": latest_health,
                "system_summary": system_summary,
                "performance_trends": performance_trends,
                "active_alerts": active_alerts,
                "alert_counts": {
                    "critical": len(
                        [a for a in active_alerts if a.get("severity") == "critical"],
                    ),
                    "error": len(
                        [a for a in active_alerts if a.get("severity") == "error"],
                    ),
                    "warning": len(
                        [a for a in active_alerts if a.get("severity") == "warning"],
                    ),
                    "info": len(
                        [a for a in active_alerts if a.get("severity") == "info"],
                    ),
                },
                "statistics": {
                    "total_health_checks": len(self.health_checks),
                    "total_alerts_today": len(
                        [
                            a
                            for a in self.active_alerts
                            if (datetime.now() - a.timestamp).total_seconds() < 86400
                        ],
                    ),
                    "avg_response_time": self._calculate_avg_response_time(),
                },
            }

    def _calculate_overall_status(self) -> str:
        """Calculate overall system status"""
        # Check for critical alerts
        critical_alerts = [
            a for a in self.active_alerts if not a.resolved and a.severity == "critical"
        ]
        if critical_alerts:
            return "critical"

        # Check for error alerts
        error_alerts = [
            a for a in self.active_alerts if not a.resolved and a.severity == "error"
        ]
        if error_alerts:
            return "error"

        # Check health status
        recent_health = {}
        for service_name in self.health_checks:
            service_results = [
                r
                for r in self.health_results
                if r.service_name == service_name
                and (datetime.now() - r.timestamp).total_seconds() < 300
            ]
            if service_results:
                latest = max(service_results, key=lambda x: x.timestamp)
                recent_health[service_name] = latest.status

        if any(status == "unhealthy" for status in recent_health.values()):
            return "unhealthy"
        if any(status == "degraded" for status in recent_health.values()):
            return "degraded"
        return "healthy"

    def _calculate_avg_response_time(self) -> float:
        """Calculate average response time"""
        recent_results = [
            r
            for r in self.health_results
            if (datetime.now() - r.timestamp).total_seconds() < 3600
            and r.response_time_ms > 0
        ]

        if recent_results:
            return statistics.mean([r.response_time_ms for r in recent_results])
        return 0.0

    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an active alert"""
        with self._lock:
            for alert in self.active_alerts:
                if alert.alert_id == alert_id and not alert.resolved:
                    alert.resolved = True
                    alert.resolved_at = datetime.now()

                    # Update in database
                    self._store_alert(alert)

                    logger.info(f"[HEALTH] Alert resolved: {alert_id}")
                    return True

        return False

    def shutdown(self):
        """Shutdown the health monitor"""
        self._running = False
        logger.info("[HEALTH] Health monitor shutdown")


# Global health monitor instance
health_monitor = None


def get_health_monitor() -> EnterpriseHealthMonitor:
    """Get global health monitor instance"""
    global health_monitor

    if health_monitor is None:
        health_monitor = EnterpriseHealthMonitor()

    return health_monitor


def initialize_health_monitoring():
    """Initialize enterprise health monitoring"""
    try:
        monitor = get_health_monitor()
        logger.info("[HEALTH] Enterprise health monitoring system initialized")
        return monitor
    except Exception as e:
        logger.error(f"[HEALTH] Failed to initialize health monitoring: {e}")
        return None


if __name__ == "__main__":
    # Test the health monitoring system
    monitor = initialize_health_monitoring()

    if monitor:
        # Wait for some data collection
        time.sleep(35)

        # Get dashboard data
        dashboard_data = monitor.get_dashboard_data()
        print(f"Dashboard data: {json.dumps(dashboard_data, indent=2)}")

        # Shutdown
        monitor.shutdown()
