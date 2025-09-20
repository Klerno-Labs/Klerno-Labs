"""
Klerno Labs - Enterprise Monitoring Dashboard
Real-time system monitoring with alerting for 0.01% quality applications
"""

import asyncio
import json
import logging
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import psutil

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """Individual metric data point."""

    timestamp: datetime
    metric_name: str
    value: float
    tags: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "metric_name": self.metric_name,
            "value": self.value,
            "tags": self.tags,
        }


@dataclass
class Alert:
    """System alert definition."""

    id: str
    name: str
    description: str
    severity: str  # critical, warning, info
    metric: str
    threshold: float
    operator: str  # gt, lt, eq
    duration: int  # seconds
    active: bool = False
    triggered_at: datetime | None = None


class EnterpriseMonitor:
    """Enterprise-grade monitoring system with real-time metrics and alerting."""

    def __init__(self, db_path: str = "./data/monitoring.db"):
        self.db_path = db_path
        self.metrics_buffer: list[MetricPoint] = []
        self.alerts: dict[str, Alert] = {}
        self.running = False
        self.collection_interval = 5  # seconds
        self.buffer_flush_interval = 30  # seconds

        # Initialize database
        self._init_database()
        self._setup_default_alerts()

    def _init_database(self) -> None:
        """Initialize monitoring database."""
        Path(self.db_path).parent.mkdir(exist_ok=True, parents=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create metrics table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                value REAL NOT NULL,
                tags TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Create alerts table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS alert_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT NOT NULL,
                alert_name TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT,
                triggered_at DATETIME,
                resolved_at DATETIME,
                duration_seconds INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Create performance index
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_metrics_timestamp
            ON metrics(timestamp)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_metrics_name_timestamp
            ON metrics(metric_name, timestamp)
        """
        )

        conn.commit()
        conn.close()

        logger.info("✅ Monitoring database initialized")

    def _setup_default_alerts(self) -> None:
        """Setup default system alerts."""
        default_alerts = [
            Alert(
                id="cpu_high",
                name="High CPU Usage",
                description="CPU usage exceeds 80% for more than 2 minutes",
                severity="warning",
                metric="system.cpu.percent",
                threshold=80.0,
                operator="gt",
                duration=120,
            ),
            Alert(
                id="memory_high",
                name="High Memory Usage",
                description="Memory usage exceeds 85% for more than 1 minute",
                severity="warning",
                metric="system.memory.percent",
                threshold=85.0,
                operator="gt",
                duration=60,
            ),
            Alert(
                id="disk_high",
                name="High Disk Usage",
                description="Disk usage exceeds 90%",
                severity="critical",
                metric="system.disk.percent",
                threshold=90.0,
                operator="gt",
                duration=30,
            ),
            Alert(
                id="response_time_high",
                name="High Response Time",
                description="Average response time exceeds 1000ms",
                severity="warning",
                metric="app.response_time.avg",
                threshold=1000.0,
                operator="gt",
                duration=60,
            ),
            Alert(
                id="error_rate_high",
                name="High Error Rate",
                description="Error rate exceeds 5%",
                severity="critical",
                metric="app.error_rate.percent",
                threshold=5.0,
                operator="gt",
                duration=60,
            ),
        ]

        for alert in default_alerts:
            self.alerts[alert.id] = alert

        logger.info(f"✅ Configured {len(default_alerts)} default alerts")

    def collect_system_metrics(self) -> list[MetricPoint]:
        """Collect comprehensive system metrics."""
        now = datetime.now()
        metrics = []

        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            metrics.append(
                MetricPoint(
                    timestamp=now,
                    metric_name="system.cpu.percent",
                    value=cpu_percent,
                    tags={"host": "localhost", "type": "system"},
                )
            )

            # Memory metrics
            memory = psutil.virtual_memory()
            metrics.append(
                MetricPoint(
                    timestamp=now,
                    metric_name="system.memory.percent",
                    value=memory.percent,
                    tags={"host": "localhost", "type": "system"},
                )
            )

            metrics.append(
                MetricPoint(
                    timestamp=now,
                    metric_name="system.memory.available_mb",
                    value=memory.available / 1024 / 1024,
                    tags={"host": "localhost", "type": "system"},
                )
            )

            # Disk metrics
            disk = psutil.disk_usage("/")
            disk_percent = (disk.used / disk.total) * 100
            metrics.append(
                MetricPoint(
                    timestamp=now,
                    metric_name="system.disk.percent",
                    value=disk_percent,
                    tags={"host": "localhost", "type": "system", "mount": "/"},
                )
            )

            # Network metrics
            network = psutil.net_io_counters()
            metrics.append(
                MetricPoint(
                    timestamp=now,
                    metric_name="system.network.bytes_sent",
                    value=network.bytes_sent,
                    tags={"host": "localhost", "type": "system"},
                )
            )

            metrics.append(
                MetricPoint(
                    timestamp=now,
                    metric_name="system.network.bytes_recv",
                    value=network.bytes_recv,
                    tags={"host": "localhost", "type": "system"},
                )
            )

            # Process metrics
            try:
                process = psutil.Process()
                metrics.append(
                    MetricPoint(
                        timestamp=now,
                        metric_name="app.memory.rss_mb",
                        value=process.memory_info().rss / 1024 / 1024,
                        tags={"host": "localhost", "type": "application"},
                    )
                )

                metrics.append(
                    MetricPoint(
                        timestamp=now,
                        metric_name="app.cpu.percent",
                        value=process.cpu_percent(),
                        tags={"host": "localhost", "type": "application"},
                    )
                )

                metrics.append(
                    MetricPoint(
                        timestamp=now,
                        metric_name="app.threads.count",
                        value=process.num_threads(),
                        tags={"host": "localhost", "type": "application"},
                    )
                )

            except psutil.NoSuchProcess:
                pass

        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")

        return metrics

    def add_metric(self, metric: MetricPoint) -> None:
        """Add a metric to the buffer."""
        self.metrics_buffer.append(metric)

    def add_custom_metric(
        self, name: str, value: float, tags: dict[str, str] = None
    ) -> None:
        """Add a custom metric."""
        metric = MetricPoint(
            timestamp=datetime.now(), metric_name=name, value=value, tags=tags or {}
        )
        self.add_metric(metric)

    def flush_metrics(self) -> None:
        """Flush metrics buffer to database."""
        if not self.metrics_buffer:
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            for metric in self.metrics_buffer:
                cursor.execute(
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

            conn.commit()
            conn.close()

            logger.debug(f"Flushed {len(self.metrics_buffer)} metrics to database")
            self.metrics_buffer.clear()

        except Exception as e:
            logger.error(f"Error flushing metrics: {e}")

    def check_alerts(self) -> list[dict[str, Any]]:
        """Check all alerts against current metrics."""
        triggered_alerts = []

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            for alert in self.alerts.values():
                # Get recent metrics for this alert
                since = datetime.now() - timedelta(seconds=alert.duration)

                cursor.execute(
                    """
                    SELECT AVG(value) as avg_value, COUNT(*) as count
                    FROM metrics
                    WHERE metric_name = ? AND timestamp >= ?
                """,
                    (alert.metric, since.isoformat()),
                )

                result = cursor.fetchone()
                if not result or result[1] == 0:
                    continue

                avg_value = result[0]

                # Check if alert condition is met
                condition_met = False
                if (
                    alert.operator == "gt"
                    and avg_value > alert.threshold
                    or alert.operator == "lt"
                    and avg_value < alert.threshold
                    or alert.operator == "eq"
                    and abs(avg_value - alert.threshold) < 0.01
                ):
                    condition_met = True

                # Handle alert state changes
                if condition_met and not alert.active:
                    # New alert triggered
                    alert.active = True
                    alert.triggered_at = datetime.now()

                    alert_data = {
                        "id": alert.id,
                        "name": alert.name,
                        "severity": alert.severity,
                        "description": alert.description,
                        "current_value": avg_value,
                        "threshold": alert.threshold,
                        "triggered_at": alert.triggered_at.isoformat(),
                    }

                    triggered_alerts.append(alert_data)

                    # Log to alert history
                    cursor.execute(
                        """
                        INSERT INTO alert_history
                        (alert_id, alert_name, severity, message, triggered_at)
                        VALUES (?, ?, ?, ?, ?)
                    """,
                        (
                            alert.id,
                            alert.name,
                            alert.severity,
                            f"{alert.description} (Current: {avg_value:.2f}, Threshold: {alert.threshold})",
                            alert.triggered_at.isoformat(),
                        ),
                    )

                    logger.warning(
                        f"🚨 Alert triggered: {alert.name} - {avg_value:.2f}"
                    )

                elif not condition_met and alert.active:
                    # Alert resolved
                    resolved_at = datetime.now()
                    duration = (resolved_at - alert.triggered_at).total_seconds()

                    cursor.execute(
                        """
                        UPDATE alert_history
                        SET resolved_at = ?, duration_seconds = ?
                        WHERE alert_id = ? AND resolved_at IS NULL
                    """,
                        (resolved_at.isoformat(), duration, alert.id),
                    )

                    alert.active = False
                    alert.triggered_at = None

                    logger.info(
                        f"✅ Alert resolved: {alert.name} after {duration:.1f}s"
                    )

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Error checking alerts: {e}")

        return triggered_alerts

    def get_dashboard_data(self, hours: int = 1) -> dict[str, Any]:
        """Get dashboard data for the last N hours."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            since = datetime.now() - timedelta(hours=hours)

            # Get recent metrics
            cursor.execute(
                """
                SELECT metric_name, AVG(value) as avg_value,
                       MIN(value) as min_value, MAX(value) as max_value,
                       COUNT(*) as count
                FROM metrics
                WHERE timestamp >= ?
                GROUP BY metric_name
                ORDER BY metric_name
            """,
                (since.isoformat(),),
            )

            metrics_summary = {}
            for row in cursor.fetchall():
                metrics_summary[row[0]] = {
                    "avg": round(row[1], 2),
                    "min": round(row[2], 2),
                    "max": round(row[3], 2),
                    "count": row[4],
                }

            # Get active alerts
            active_alerts = [
                {
                    "id": alert.id,
                    "name": alert.name,
                    "severity": alert.severity,
                    "triggered_at": (
                        alert.triggered_at.isoformat() if alert.triggered_at else None
                    ),
                }
                for alert in self.alerts.values()
                if alert.active
            ]

            # Get recent alert history
            cursor.execute(
                """
                SELECT alert_name, severity, triggered_at, resolved_at, duration_seconds
                FROM alert_history
                WHERE triggered_at >= ?
                ORDER BY triggered_at DESC
                LIMIT 50
            """,
                (since.isoformat(),),
            )

            alert_history = []
            for row in cursor.fetchall():
                alert_history.append(
                    {
                        "name": row[0],
                        "severity": row[1],
                        "triggered_at": row[2],
                        "resolved_at": row[3],
                        "duration": row[4],
                    }
                )

            conn.close()

            return {
                "timestamp": datetime.now().isoformat(),
                "metrics_summary": metrics_summary,
                "active_alerts": active_alerts,
                "alert_history": alert_history,
                "system_status": "healthy" if not active_alerts else "degraded",
            }

        except Exception as e:
            logger.error(f"Error getting dashboard data: {e}")
            return {"error": str(e)}

    async def run_monitoring_loop(self) -> None:
        """Main monitoring loop."""
        logger.info("🔍 Starting monitoring loop...")
        self.running = True

        last_flush = time.time()

        while self.running:
            try:
                # Collect system metrics
                system_metrics = self.collect_system_metrics()
                for metric in system_metrics:
                    self.add_metric(metric)

                # Check alerts
                triggered_alerts = self.check_alerts()
                for alert in triggered_alerts:
                    logger.warning(
                        f"🚨 ALERT: {alert['name']} - {alert['description']}"
                    )

                # Flush metrics periodically
                if time.time() - last_flush >= self.buffer_flush_interval:
                    self.flush_metrics()
                    last_flush = time.time()

                await asyncio.sleep(self.collection_interval)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)

    def stop(self) -> None:
        """Stop the monitoring system."""
        logger.info("🛑 Stopping monitoring system...")
        self.running = False
        self.flush_metrics()


# Global monitor instance
monitor = EnterpriseMonitor()


async def start_monitoring():
    """Start the monitoring system."""
    await monitor.run_monitoring_loop()


def get_monitor() -> EnterpriseMonitor:
    """Get the global monitor instance."""
    return monitor
