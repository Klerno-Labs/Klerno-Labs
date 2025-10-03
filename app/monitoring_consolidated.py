"""
Klerno Labs - Consolidated Monitoring System
Enterprise-grade monitoring, alerting, and observability
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# =============================================================================
# Core Monitoring Models
# =============================================================================


@dataclass
class MetricPoint:
    """Simple metric point used by the monitor buffer."""

    timestamp: datetime
    metric_name: str
    value: float
    tags: dict[str, str]


@dataclass
class AlertRule:
    """Alert rule configuration."""

    name: str
    metric: str
    threshold: float
    operator: str  # >, <, >=, <=, ==
    duration: int  # seconds
    severity: str  # low, medium, high, critical
    enabled: bool = True


@dataclass
class Alert:
    """Active alert instance."""

    rule_name: str
    message: str
    severity: str
    timestamp: datetime
    resolved: bool = False
    resolved_at: datetime | None = None


class MonitoringStatus(str, Enum):
    """System monitoring status."""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


# =============================================================================
# Enhanced Monitoring System
# =============================================================================


class EnhancedMonitor:
    """Enterprise monitoring with real-time alerting."""

    def __init__(self, db_path: str = "./data/monitoring.db") -> None:
        self.db_path = db_path
        self.metrics_buffer: deque[MetricPoint] = deque(maxlen=10000)
        self.alerts: list[Alert] = []
        self.alert_rules: list[AlertRule] = []
        self._lock = threading.Lock()
        self._running = False

        # Initialize database
        self._init_database()

        # Load default alert rules
        self._load_default_rules()

    def _init_database(self) -> None:
        """Initialize monitoring database."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            # Metrics table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    value REAL NOT NULL,
                    tags TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Alerts table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_name TEXT NOT NULL,
                    message TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    resolved INTEGER DEFAULT 0,
                    resolved_at TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Alert rules table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS alert_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    metric TEXT NOT NULL,
                    threshold REAL NOT NULL,
                    operator TEXT NOT NULL,
                    duration INTEGER NOT NULL,
                    severity TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Indexes
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(metric_name)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp)"
            )

    def _load_default_rules(self) -> None:
        """Load default monitoring rules."""
        default_rules = [
            AlertRule(
                name="high_cpu_usage",
                metric="cpu_percent",
                threshold=80.0,
                operator=">",
                duration=300,  # 5 minutes
                severity="high",
            ),
            AlertRule(
                name="high_memory_usage",
                metric="memory_percent",
                threshold=85.0,
                operator=">",
                duration=300,
                severity="high",
            ),
            AlertRule(
                name="disk_space_low",
                metric="disk_usage_percent",
                threshold=90.0,
                operator=">",
                duration=60,
                severity="critical",
            ),
            AlertRule(
                name="response_time_high",
                metric="avg_response_time_ms",
                threshold=5000.0,
                operator=">",
                duration=180,
                severity="medium",
            ),
        ]

        for rule in default_rules:
            self.add_alert_rule(rule)

    def add_alert_rule(self, rule: AlertRule) -> None:
        """Add an alert rule."""
        with self._lock:
            # Remove existing rule with same name
            self.alert_rules = [r for r in self.alert_rules if r.name != rule.name]
            self.alert_rules.append(rule)

        # Persist to database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO alert_rules
                (name, metric, threshold, operator, duration, severity, enabled)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    rule.name,
                    rule.metric,
                    rule.threshold,
                    rule.operator,
                    rule.duration,
                    rule.severity,
                    rule.enabled,
                ),
            )

    def record_metric(
        self, name: str, value: float, tags: dict[str, str] | None = None
    ) -> None:
        """Record a metric point."""
        metric = MetricPoint(
            timestamp=datetime.now(UTC), metric_name=name, value=value, tags=tags or {}
        )

        with self._lock:
            self.metrics_buffer.append(metric)

        # Check for alerts
        self._check_alerts(metric)

        # Async persist to database
        asyncio.create_task(self._persist_metric(metric))

    async def _persist_metric(self, metric: MetricPoint) -> None:
        """Persist metric to database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO metrics (timestamp, metric_name, value, tags)
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        metric.timestamp.isoformat(),
                        metric.metric_name,
                        metric.value,
                        json.dumps(metric.tags),
                    ),
                )
        except Exception as e:
            logger.error(f"Failed to persist metric: {e}")

    def _check_alerts(self, metric: MetricPoint) -> None:
        """Check if metric triggers any alerts."""
        for rule in self.alert_rules:
            if not rule.enabled or rule.metric != metric.metric_name:
                continue

            # Evaluate threshold
            triggered = False
            if rule.operator == ">":
                triggered = metric.value > rule.threshold
            elif rule.operator == "<":
                triggered = metric.value < rule.threshold
            elif rule.operator == ">=":
                triggered = metric.value >= rule.threshold
            elif rule.operator == "<=":
                triggered = metric.value <= rule.threshold
            elif rule.operator == "==":
                triggered = metric.value == rule.threshold

            if triggered:
                self._trigger_alert(rule, metric)

    def _trigger_alert(self, rule: AlertRule, metric: MetricPoint) -> None:
        """Trigger an alert."""
        # Check if alert already exists and is not resolved
        existing_alert = next(
            (a for a in self.alerts if a.rule_name == rule.name and not a.resolved),
            None,
        )

        if existing_alert:
            return  # Alert already active

        alert = Alert(
            rule_name=rule.name,
            message=f"{rule.name}: {metric.metric_name} = {metric.value} {rule.operator} {rule.threshold}",
            severity=rule.severity,
            timestamp=metric.timestamp,
        )

        with self._lock:
            self.alerts.append(alert)

        # Persist alert
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO alerts (rule_name, message, severity, timestamp)
                VALUES (?, ?, ?, ?)
            """,
                (
                    alert.rule_name,
                    alert.message,
                    alert.severity,
                    alert.timestamp.isoformat(),
                ),
            )

        logger.warning(f"Alert triggered: {alert.message}")

    def resolve_alert(self, rule_name: str) -> None:
        """Resolve an active alert."""
        with self._lock:
            for alert in self.alerts:
                if alert.rule_name == rule_name and not alert.resolved:
                    alert.resolved = True
                    alert.resolved_at = datetime.now(UTC)

                    # Update database
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute(
                            """
                            UPDATE alerts
                            SET resolved = 1, resolved_at = ?
                            WHERE rule_name = ? AND resolved = 0
                        """,
                            (alert.resolved_at.isoformat(), rule_name),
                        )
                    break

    def get_system_status(self) -> MonitoringStatus:
        """Get overall system health status."""
        active_alerts = [a for a in self.alerts if not a.resolved]

        if not active_alerts:
            return MonitoringStatus.HEALTHY

        critical_alerts = [a for a in active_alerts if a.severity == "critical"]
        high_alerts = [a for a in active_alerts if a.severity == "high"]

        if critical_alerts:
            return MonitoringStatus.CRITICAL
        elif high_alerts:
            return MonitoringStatus.WARNING
        else:
            return MonitoringStatus.WARNING

    def get_metrics_summary(self, hours: int = 24) -> dict[str, Any]:
        """Get metrics summary for specified time period."""
        cutoff = datetime.now(UTC) - timedelta(hours=hours)

        with self._lock:
            recent_metrics = [m for m in self.metrics_buffer if m.timestamp >= cutoff]

        if not recent_metrics:
            return {"message": "No metrics available"}

        # Group by metric name
        metrics_by_name: dict[str, list[float]] = defaultdict(list[Any])
        for metric in recent_metrics:
            metrics_by_name[metric.metric_name].append(metric.value)

        summary = {}
        for name, values in metrics_by_name.items():
            if values:
                summary[name] = {
                    "count": len(values),
                    "avg": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "latest": values[-1],
                }

        return {
            "period_hours": hours,
            "total_data_points": len(recent_metrics),
            "metrics": summary,
            "active_alerts": len([a for a in self.alerts if not a.resolved]),
            "system_status": self.get_system_status().value,
        }

    def get_active_alerts(self) -> list[dict[str, Any]]:
        """Get all active alerts."""
        active_alerts = [a for a in self.alerts if not a.resolved]

        return [
            {
                "rule_name": alert.rule_name,
                "message": alert.message,
                "severity": alert.severity,
                "timestamp": alert.timestamp.isoformat(),
                "duration_seconds": (
                    datetime.now(UTC) - alert.timestamp
                ).total_seconds(),
            }
            for alert in active_alerts
        ]

    def start_monitoring(self) -> None:
        """Start background monitoring."""
        if self._running:
            return

        self._running = True

        def monitor_loop() -> None:
            while self._running:
                try:
                    self._collect_system_metrics()
                    time.sleep(60)  # Collect every minute
                except Exception as e:
                    logger.error(f"Monitoring error: {e}")
                    time.sleep(60)

        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()
        logger.info("Enhanced monitoring started")

    def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        self._running = False
        logger.info("Enhanced monitoring stopped")

    def _collect_system_metrics(self) -> None:
        """Collect system metrics."""
        try:
            import psutil

            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            self.record_metric("cpu_percent", cpu_percent)

            # Memory metrics
            memory = psutil.virtual_memory()
            self.record_metric("memory_percent", memory.percent)
            self.record_metric("memory_available_mb", memory.available / (1024 * 1024))

            # Disk metrics
            disk = psutil.disk_usage("/")
            self.record_metric("disk_usage_percent", disk.percent)
            self.record_metric("disk_free_gb", disk.free / (1024 * 1024 * 1024))

            # Network metrics
            net_io = psutil.net_io_counters()
            self.record_metric("network_bytes_sent", net_io.bytes_sent)
            self.record_metric("network_bytes_recv", net_io.bytes_recv)

            # Process metrics
            process_count = len(psutil.pids())
            self.record_metric("process_count", process_count)

        except ImportError:
            # psutil not available, record basic metrics
            self.record_metric("cpu_percent", 0.0)
            self.record_metric("memory_percent", 0.0)

        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")


# =============================================================================
# Health Check System
# =============================================================================


class HealthChecker:
    """Comprehensive health checking system."""

    def __init__(self, monitor: EnhancedMonitor) -> None:
        self.monitor = monitor
        self.health_checks: dict[str, Callable[[], bool]] = {}

    def register_check(self, name: str, check_func: Callable[[], bool]) -> None:
        """Register a health check function."""
        self.health_checks[name] = check_func

    def run_all_checks(self) -> dict[str, Any]:
        """Run all registered health checks."""
        results = {}
        overall_healthy = True

        for name, check_func in self.health_checks.items():
            try:
                result = check_func()
                results[name] = {"healthy": result, "error": None}
                if not result:
                    overall_healthy = False
            except Exception as e:
                results[name] = {"healthy": False, "error": str(e)}
                overall_healthy = False

        return {
            "overall_healthy": overall_healthy,
            "checks": results,
            "timestamp": datetime.now(UTC).isoformat(),
            "system_status": self.monitor.get_system_status().value,
        }


# =============================================================================
# Global Monitoring Manager
# =============================================================================


class MonitoringManager:
    """Centralized monitoring management."""

    def __init__(self) -> None:
        self.monitor = EnhancedMonitor()
        self.health_checker = HealthChecker(self.monitor)
        self._setup_default_checks()

    def _setup_default_checks(self) -> None:
        """Setup default health checks."""

        def check_memory() -> bool:
            try:
                import psutil

                return psutil.virtual_memory().percent < 95
            except ImportError:
                return True

        def check_disk_space() -> bool:
            try:
                import psutil

                return psutil.disk_usage("/").percent < 95
            except (ImportError, FileNotFoundError):
                return True

        self.health_checker.register_check("memory", check_memory)
        self.health_checker.register_check("disk_space", check_disk_space)

    def start(self) -> None:
        """Start monitoring."""
        self.monitor.start_monitoring()

    def stop(self) -> None:
        """Stop monitoring."""
        self.monitor.stop_monitoring()

    def get_status(self) -> dict[str, Any]:
        """Get comprehensive monitoring status."""
        return {
            "monitoring": self.monitor.get_metrics_summary(),
            "health": self.health_checker.run_all_checks(),
            "alerts": self.monitor.get_active_alerts(),
        }


# Global instance
monitoring_manager = MonitoringManager()
