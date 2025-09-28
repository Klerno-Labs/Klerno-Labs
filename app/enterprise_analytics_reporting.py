"""
Klerno Labs Enterprise Analytics & Business Intelligence System
Advanced analytics, reporting, and business intelligence capabilities
"""

import json
import logging
import sqlite3
import threading
import time
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from app._typing_shims import ISyncConnection
from app.constants import CACHE_TTL


def _ensure_numpy() -> None:
    if "np" in globals():
        return
    try:
        import importlib

        np = importlib.import_module("numpy")
        globals()["np"] = np
    except ImportError as e:
        raise RuntimeError("numpy is required for analytics computations") from e
    except Exception:
        raise


if TYPE_CHECKING:
    # Avoid requiring heavy optional dependencies in dev envs; treat as Any.
    np: Any
    pd: Any
else:
    # At runtime we lazily load these; initialize to None so the names exist
    # (the helper functions _ensure_numpy/_ensure_pandas will populate them).
    np = None
    pd = None


def _ensure_pandas() -> None:
    if "pd" in globals():
        return
    try:
        import importlib

        pd = importlib.import_module("pandas")
        globals()["pd"] = pd
    except ImportError:
        raise RuntimeError("pandas is required for reporting features")


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AnalyticsEvent:
    """Analytics event record"""

    event_id: str
    event_type: str
    timestamp: datetime
    user_id: str | None = None
    session_id: str | None = None
    properties: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReportConfig:
    """Report configuration"""

    report_id: str
    report_name: str
    description: str
    query_template: str
    parameters: dict[str, Any] = field(default_factory=dict)
    schedule: str | None = None  # cron-like schedule
    output_format: str = "json"  # json, csv, pdf, html
    recipients: list[str] = field(default_factory=list)


@dataclass
class BusinessMetric:
    """Business metric definition"""

    metric_id: str
    metric_name: str
    description: str
    calculation_function: str
    target_value: float | None = None
    threshold_warning: float | None = None
    threshold_critical: float | None = None
    unit: str = ""
    category: str = "general"


class EnterpriseAnalytics:
    """Comprehensive enterprise analytics system"""

    def __init__(self, database_path: str = "./data/klerno.db"):
        self.database_path = database_path
        self.events: list[AnalyticsEvent] = []
        self.reports: dict[str, ReportConfig] = {}
        self.metrics: dict[str, BusinessMetric] = {}
        self.cached_results: dict[str, dict] = {}

        # Configuration
        self.event_retention_days = 90
        self.cache_ttl_seconds = CACHE_TTL

        # Threading
        self._lock = threading.RLock()
        self._running = True

        # Initialize database
        self._init_database()

        # Start background workers
        self._analytics_thread = threading.Thread(
            target=self._analytics_worker, daemon=True
        )
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_worker, daemon=True
        )

        self._analytics_thread.start()
        self._cleanup_thread.start()

        # Register default metrics and reports
        self._register_default_metrics()
        self._register_default_reports()

        logger.info("[ANALYTICS] Enterprise analytics system initialized")

    def _init_database(self):
        """Initialize analytics database"""
        try:
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)

            conn = cast(ISyncConnection, sqlite3.connect(self.database_path))
            cursor = conn.cursor()

            # Analytics events table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS analytics_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    user_id TEXT,
                    session_id TEXT,
                    properties TEXT,
                    metadata TEXT
                )
            """
            )

            # User sessions table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    user_id TEXT,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    duration_seconds INTEGER,
                    page_views INTEGER DEFAULT 0,
                    events_count INTEGER DEFAULT 0,
                    user_agent TEXT,
                    ip_address TEXT,
                    country TEXT,
                    city TEXT
                )
            """
            )

            # Business metrics table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS business_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    value REAL NOT NULL,
                    metadata TEXT
                )
            """
            )

            # Report executions table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS report_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id TEXT NOT NULL,
                    execution_time TEXT NOT NULL,
                    duration_seconds REAL NOT NULL,
                    status TEXT NOT NULL,
                    result_data TEXT,
                    error_message TEXT
                )
            """
            )

            # Create indices for performance
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_timestamp ON analytics_events(timestamp)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_type ON analytics_events(event_type)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_user ON analytics_events(user_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_sessions_start ON user_sessions(start_time)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON business_metrics(timestamp)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_metrics_id ON business_metrics(metric_id)"
            )

            conn.commit()
            conn.close()

            logger.info("[ANALYTICS] Database initialized")

        except Exception as e:
            logger.error(f"[ANALYTICS] Database initialization failed: {e}")

    def track_event(
        self,
        event_type: str,
        user_id: str | None = None,
        session_id: str | None = None,
        properties: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Track an analytics event"""

        event_id = f"{event_type}_{int(time.time() * 1000)}_{hash(str(properties))}"

        event = AnalyticsEvent(
            event_id=event_id,
            event_type=event_type,
            timestamp=datetime.now(),
            user_id=user_id,
            session_id=session_id,
            properties=properties or {},
            metadata=metadata or {},
        )

        with self._lock:
            self.events.append(event)
            self._store_event(event)

        logger.debug(f"[ANALYTICS] Tracked event: {event_type}")
        return event_id

    def _store_event(self, event: AnalyticsEvent):
        """Store event in database"""
        try:
            conn = cast(ISyncConnection, sqlite3.connect(self.database_path))
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO analytics_events
                (event_id, event_type, timestamp, user_id, session_id, properties, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    event.event_id,
                    event.event_type,
                    event.timestamp.isoformat(),
                    event.user_id,
                    event.session_id,
                    json.dumps(event.properties),
                    json.dumps(event.metadata),
                ),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"[ANALYTICS] Failed to store event: {e}")

    def register_metric(self, metric: BusinessMetric):
        """Register a business metric"""
        with self._lock:
            self.metrics[metric.metric_id] = metric
            logger.info(f"[ANALYTICS] Registered metric: {metric.metric_name}")

    def register_report(self, report: ReportConfig):
        """Register a report configuration"""
        with self._lock:
            self.reports[report.report_id] = report
            logger.info(f"[ANALYTICS] Registered report: {report.report_name}")

    def _register_default_metrics(self):
        """Register default business metrics"""

        # User engagement metrics
        self.register_metric(
            BusinessMetric(
                metric_id="daily_active_users",
                metric_name="Daily Active Users",
                description="Number of unique users active in the last 24 hours",
                calculation_function="count_unique_users_24h",
                target_value=100,
                threshold_warning=50,
                threshold_critical=25,
                unit="users",
                category="engagement",
            )
        )

        self.register_metric(
            BusinessMetric(
                metric_id="session_duration_avg",
                metric_name="Average Session Duration",
                description="Average duration of user sessions",
                calculation_function="avg_session_duration",
                target_value=300,  # 5 minutes
                threshold_warning=180,  # 3 minutes
                threshold_critical=60,  # 1 minute
                unit="seconds",
                category="engagement",
            )
        )

        # System performance metrics
        self.register_metric(
            BusinessMetric(
                metric_id="api_response_time_p95",
                metric_name="API Response Time P95",
                description="95th percentile API response time",
                calculation_function="api_response_time_p95",
                target_value=500,  # 500ms
                threshold_warning=1000,  # 1s
                threshold_critical=2000,  # 2s
                unit="milliseconds",
                category="performance",
            )
        )

        # Business metrics
        self.register_metric(
            BusinessMetric(
                metric_id="conversion_rate",
                metric_name="Conversion Rate",
                description="Percentage of visitors who complete desired action",
                calculation_function="calculate_conversion_rate",
                target_value=5.0,  # 5%
                threshold_warning=3.0,  # 3%
                threshold_critical=1.0,  # 1%
                unit="percent",
                category="business",
            )
        )

    def _register_default_reports(self):
        """Register default reports"""

        # Daily summary report
        self.register_report(
            ReportConfig(
                report_id="daily_summary",
                report_name="Daily Summary Report",
                description="Daily overview of key metrics and events",
                query_template="""
                SELECT
                    DATE(timestamp) as date,
                    COUNT(*) as total_events,
                    COUNT(DISTINCT user_id) as unique_users,
                    COUNT(DISTINCT session_id) as unique_sessions
                FROM analytics_events
                WHERE timestamp >= date('now', '-1 day')
                GROUP BY DATE(timestamp)
            """,
                schedule="0 9 * * *",  # Daily at 9 AM
                output_format="json",
            )
        )

        # User behavior report
        self.register_report(
            ReportConfig(
                report_id="user_behavior",
                report_name="User Behavior Analysis",
                description="Analysis of user behavior patterns",
                query_template="""
                SELECT
                    event_type,
                    COUNT(*) as event_count,
                    COUNT(DISTINCT user_id) as unique_users,
                    AVG(CASE WHEN json_extract(properties, '$.duration') IS NOT NULL
                        THEN json_extract(properties, '$.duration') END) as avg_duration
                FROM analytics_events
                WHERE timestamp >= date('now', '-7 days')
                GROUP BY event_type
                ORDER BY event_count DESC
            """,
                schedule="0 0 * * 1",  # Weekly on Monday
                output_format="json",
            )
        )

        # Performance report
        self.register_report(
            ReportConfig(
                report_id="performance_analysis",
                report_name="Performance Analysis Report",
                description="System performance analysis and trends",
                query_template="""
                SELECT
                    DATE(timestamp) as date,
                    metric_id,
                    AVG(value) as avg_value,
                    MIN(value) as min_value,
                    MAX(value) as max_value
                FROM business_metrics
                WHERE timestamp >= date('now', '-30 days')
                  AND metric_id IN ('api_response_time_p95', 'session_duration_avg')
                GROUP BY DATE(timestamp), metric_id
                ORDER BY date DESC, metric_id
            """,
                schedule="0 8 * * *",  # Daily at 8 AM
                output_format="json",
            )
        )

    def calculate_metric(
        self,
        metric_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
        """Calculate a business metric"""

        if metric_id not in self.metrics:
            raise ValueError(f"Unknown metric: {metric_id}")

        metric = self.metrics[metric_id]

        # Set default time range
        if end_time is None:
            end_time = datetime.now()
        if start_time is None:
            start_time = end_time - timedelta(days=1)

        # Check cache
        cache_key = f"{metric_id}_{start_time.isoformat()}_{end_time.isoformat()}"
        if cache_key in self.cached_results:
            cached = self.cached_results[cache_key]
            if (
                datetime.now() - datetime.fromisoformat(cached["calculated_at"])
            ).total_seconds() < self.cache_ttl_seconds:
                return cached

        try:
            # Calculate metric based on function name
            calculation_func = getattr(self, metric.calculation_function, None)
            if calculation_func:
                value = calculation_func(start_time, end_time)
            else:
                value = self._calculate_generic_metric(metric_id, start_time, end_time)

            result = {
                "metric_id": metric_id,
                "metric_name": metric.metric_name,
                "value": value,
                "unit": metric.unit,
                "category": metric.category,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "calculated_at": datetime.now().isoformat(),
                "status": self._get_metric_status(metric, value),
            }

            # Cache result
            self.cached_results[cache_key] = result

            # Store in database
            self._store_metric_value(metric_id, value)

            return result

        except Exception as e:
            logger.error(f"[ANALYTICS] Failed to calculate metric {metric_id}: {e}")
            return {
                "metric_id": metric_id,
                "error": str(e),
                "calculated_at": datetime.now().isoformat(),
            }

    def _get_metric_status(self, metric: BusinessMetric, value: float) -> str:
        """Get metric status based on thresholds"""
        if metric.threshold_critical is not None and value <= metric.threshold_critical:
            return "critical"
        elif metric.threshold_warning is not None and value <= metric.threshold_warning:
            return "warning"
        elif metric.target_value is not None and value >= metric.target_value:
            return "excellent"
        else:
            return "good"

    def count_unique_users_24h(self, start_time: datetime, end_time: datetime) -> int:
        """Calculate daily active users"""
        try:
            conn = cast(ISyncConnection, sqlite3.connect(self.database_path))
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT COUNT(DISTINCT user_id)
                FROM analytics_events
                WHERE timestamp BETWEEN ? AND ? AND user_id IS NOT NULL
            """,
                (start_time.isoformat(), end_time.isoformat()),
            )

            result = cursor.fetchone()[0] or 0
            conn.close()

            return result

        except Exception as e:
            logger.error(f"[ANALYTICS] Failed to calculate DAU: {e}")
            return 0

    def avg_session_duration(self, start_time: datetime, end_time: datetime) -> float:
        """Calculate average session duration"""
        try:
            conn = cast(ISyncConnection, sqlite3.connect(self.database_path))
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT AVG(duration_seconds)
                FROM user_sessions
                WHERE start_time BETWEEN ? AND ? AND duration_seconds IS NOT NULL
            """,
                (start_time.isoformat(), end_time.isoformat()),
            )

            result = cursor.fetchone()[0] or 0
            conn.close()

            return float(result)

        except Exception as e:
            logger.error(f"[ANALYTICS] Failed to calculate avg session duration: {e}")
            return 0.0

    def api_response_time_p95(self, start_time: datetime, end_time: datetime) -> float:
        """Calculate 95th percentile API response time"""
        try:
            _ensure_numpy()
            conn = cast(ISyncConnection, sqlite3.connect(self.database_path))
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT json_extract(properties, '$.response_time') as response_time
                FROM analytics_events
                WHERE timestamp BETWEEN ? AND ?
                  AND event_type = 'api_request'
                  AND json_extract(properties, '$.response_time') IS NOT NULL
            """,
                (start_time.isoformat(), end_time.isoformat()),
            )

            response_times = [float(row[0]) for row in cursor.fetchall()]
            conn.close()

            if response_times:
                return float(np.percentile(response_times, 95))
            return 0.0

        except Exception as e:
            logger.error(f"[ANALYTICS] Failed to calculate API response time P95: {e}")
            return 0.0

    def calculate_conversion_rate(
        self, start_time: datetime, end_time: datetime
    ) -> float:
        """Calculate conversion rate"""
        try:
            conn = cast(ISyncConnection, sqlite3.connect(self.database_path))
            cursor = conn.cursor()

            # Count visitors
            cursor.execute(
                """
                SELECT COUNT(DISTINCT session_id)
                FROM analytics_events
                WHERE timestamp BETWEEN ? AND ?
                  AND event_type = 'page_view'
            """,
                (start_time.isoformat(), end_time.isoformat()),
            )

            visitors = cursor.fetchone()[0] or 0

            # Count conversions
            cursor.execute(
                """
                SELECT COUNT(DISTINCT session_id)
                FROM analytics_events
                WHERE timestamp BETWEEN ? AND ?
                  AND event_type = 'conversion'
            """,
                (start_time.isoformat(), end_time.isoformat()),
            )

            conversions = cursor.fetchone()[0] or 0
            conn.close()

            if visitors > 0:
                return (conversions / visitors) * 100
            return 0.0

        except Exception as e:
            logger.error(f"[ANALYTICS] Failed to calculate conversion rate: {e}")
            return 0.0

    def _calculate_generic_metric(
        self, metric_id: str, start_time: datetime, end_time: datetime
    ) -> float:
        """Calculate generic metric from stored values"""
        try:
            conn = cast(ISyncConnection, sqlite3.connect(self.database_path))
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT AVG(value)
                FROM business_metrics
                WHERE metric_id = ? AND timestamp BETWEEN ? AND ?
            """,
                (metric_id, start_time.isoformat(), end_time.isoformat()),
            )

            result = cursor.fetchone()[0] or 0
            conn.close()

            return float(result)

        except Exception as e:
            logger.error(
                f"[ANALYTICS] Failed to calculate generic metric {metric_id}: {e}"
            )
            return 0.0

    def _store_metric_value(self, metric_id: str, value: float):
        """Store calculated metric value"""
        try:
            conn = cast(ISyncConnection, sqlite3.connect(self.database_path))
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO business_metrics (metric_id, timestamp, value, metadata)
                VALUES (?, ?, ?, ?)
            """,
                (
                    metric_id,
                    datetime.now().isoformat(),
                    value,
                    json.dumps({"calculation_type": "automatic"}),
                ),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"[ANALYTICS] Failed to store metric value: {e}")

    def generate_report(
        self, report_id: str, parameters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Generate a report"""

        if report_id not in self.reports:
            raise ValueError(f"Unknown report: {report_id}")

        report_config = self.reports[report_id]
        start_time = datetime.now()

        try:
            # Execute report query
            conn = cast(ISyncConnection, sqlite3.connect(self.database_path))

            # Substitute parameters in query
            query = report_config.query_template
            if parameters:
                for key, value in parameters.items():
                    query = query.replace(f"${key}", str(value))

            # Execute query
            _ensure_pandas()
            df = pd.read_sql_query(query, conn)
            conn.close()

            # Format result based on output format
            result_data: Sequence[Mapping[str, Any]] | str
            if report_config.output_format == "json":
                from typing import cast

                result_data = cast(
                    Sequence[Mapping[str, Any]], df.to_dict(orient="records")
                )
            elif report_config.output_format == "csv":
                result_data = df.to_csv(index=False)
            else:
                from typing import cast

                result_data = cast(
                    Sequence[Mapping[str, Any]], df.to_dict(orient="records")
                )

            execution_time = (datetime.now() - start_time).total_seconds()

            result = {
                "report_id": report_id,
                "report_name": report_config.report_name,
                "generated_at": datetime.now().isoformat(),
                "execution_time_seconds": execution_time,
                "status": "success",
                "data": result_data,
                "row_count": len(df),
                "parameters": parameters or {},
            }

            # Store execution record
            self._store_report_execution(report_id, execution_time, "success", result)

            logger.info(f"[ANALYTICS] Generated report: {report_config.report_name}")
            return result

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()

            result = {
                "report_id": report_id,
                "report_name": report_config.report_name,
                "generated_at": datetime.now().isoformat(),
                "execution_time_seconds": execution_time,
                "status": "error",
                "error": str(e),
                "parameters": parameters or {},
            }

            # Store execution record
            self._store_report_execution(
                report_id, execution_time, "error", result, str(e)
            )

            logger.error(f"[ANALYTICS] Failed to generate report {report_id}: {e}")
            return result

    def _store_report_execution(
        self,
        report_id: str,
        duration: float,
        status: str,
        result_data: dict,
        error: str | None = None,
    ) -> None:
        """Store report execution record"""
        try:
            conn = cast(ISyncConnection, sqlite3.connect(self.database_path))
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO report_executions
                (report_id, execution_time, duration_seconds, status, result_data, error_message)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    report_id,
                    datetime.now().isoformat(),
                    duration,
                    status,
                    json.dumps(result_data) if status == "success" else None,
                    error,
                ),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"[ANALYTICS] Failed to store report execution: {e}")

    def get_analytics_dashboard(self) -> dict[str, Any]:
        """Get comprehensive analytics dashboard data"""

        # Calculate key metrics
        key_metrics = {}
        for metric_id in [
            "daily_active_users",
            "session_duration_avg",
            "api_response_time_p95",
            "conversion_rate",
        ]:
            if metric_id in self.metrics:
                try:
                    metric_result = self.calculate_metric(metric_id)
                    key_metrics[metric_id] = metric_result
                except Exception as e:
                    logger.error(
                        f"[ANALYTICS] Failed to calculate metric {metric_id}: {e}"
                    )

        # Get recent events summary
        recent_events = self._get_recent_events_summary()

        # Get user activity trends
        user_trends = self._get_user_activity_trends()

        # Get top events
        top_events = self._get_top_events()

        # Get performance trends
        performance_trends = self._get_performance_trends()

        return {
            "timestamp": datetime.now().isoformat(),
            "key_metrics": key_metrics,
            "recent_events": recent_events,
            "user_trends": user_trends,
            "top_events": top_events,
            "performance_trends": performance_trends,
            "total_events_today": self._count_events_today(),
            "active_users_today": self._count_active_users_today(),
            "total_reports": len(self.reports),
            "total_metrics": len(self.metrics),
        }

    def _get_recent_events_summary(self) -> dict[str, Any]:
        """Get summary of recent events"""
        try:
            conn = cast(ISyncConnection, sqlite3.connect(self.database_path))
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    event_type,
                    COUNT(*) as count,
                    COUNT(DISTINCT user_id) as unique_users
                FROM analytics_events
                WHERE timestamp >= datetime('now', '-1 hour')
                GROUP BY event_type
                ORDER BY count DESC
                LIMIT 10
            """
            )

            results = cursor.fetchall()
            conn.close()

            return {
                "time_period": "last_hour",
                "event_summary": [
                    {"event_type": row[0], "count": row[1], "unique_users": row[2]}
                    for row in results
                ],
            }

        except Exception as e:
            logger.error(f"[ANALYTICS] Failed to get recent events summary: {e}")
            return {"event_summary": []}

    def _get_user_activity_trends(self) -> dict[str, Any]:
        """Get user activity trends"""
        try:
            conn = cast(ISyncConnection, sqlite3.connect(self.database_path))
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    DATE(timestamp) as date,
                    COUNT(DISTINCT user_id) as unique_users,
                    COUNT(*) as total_events
                FROM analytics_events
                WHERE timestamp >= date('now', '-7 days')
                  AND user_id IS NOT NULL
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            """
            )

            results = cursor.fetchall()
            conn.close()

            return {
                "time_period": "last_7_days",
                "daily_trends": [
                    {"date": row[0], "unique_users": row[1], "total_events": row[2]}
                    for row in results
                ],
            }

        except Exception as e:
            logger.error(f"[ANALYTICS] Failed to get user activity trends: {e}")
            return {"daily_trends": []}

    def _get_top_events(self) -> list[dict[str, Any]]:
        """Get top events by frequency"""
        try:
            conn = cast(ISyncConnection, sqlite3.connect(self.database_path))
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    event_type,
                    COUNT(*) as frequency,
                    COUNT(DISTINCT user_id) as unique_users,
                    AVG(CASE WHEN json_extract(properties, '$.duration') IS NOT NULL
                        THEN json_extract(properties, '$.duration') END) as avg_duration
                FROM analytics_events
                WHERE timestamp >= date('now', '-7 days')
                GROUP BY event_type
                ORDER BY frequency DESC
                LIMIT 20
            """
            )

            results = cursor.fetchall()
            conn.close()

            return [
                {
                    "event_type": row[0],
                    "frequency": row[1],
                    "unique_users": row[2],
                    "avg_duration": row[3] if row[3] else None,
                }
                for row in results
            ]

        except Exception as e:
            logger.error(f"[ANALYTICS] Failed to get top events: {e}")
            return []

    def _get_performance_trends(self) -> dict[str, Any]:
        """Get performance trends"""
        try:
            conn = cast(ISyncConnection, sqlite3.connect(self.database_path))
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    DATE(timestamp) as date,
                    metric_id,
                    AVG(value) as avg_value
                FROM business_metrics
                WHERE timestamp >= date('now', '-30 days')
                  AND metric_id IN ('api_response_time_p95', 'session_duration_avg')
                GROUP BY DATE(timestamp), metric_id
                ORDER BY date DESC
            """
            )

            results = cursor.fetchall()
            conn.close()

            # Group by metric
            trends = defaultdict(list)
            for row in results:
                trends[row[1]].append({"date": row[0], "value": row[2]})

            return dict(trends)

        except Exception as e:
            logger.error(f"[ANALYTICS] Failed to get performance trends: {e}")
            return {}

    def _count_events_today(self) -> int:
        """Count total events today"""
        try:
            conn = cast(ISyncConnection, sqlite3.connect(self.database_path))
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM analytics_events
                WHERE date(timestamp) = date('now')
            """
            )

            result = cursor.fetchone()[0] or 0
            conn.close()

            return result

        except Exception as e:
            logger.error(f"[ANALYTICS] Failed to count events today: {e}")
            return 0

    def _count_active_users_today(self) -> int:
        """Count active users today"""
        try:
            conn = cast(ISyncConnection, sqlite3.connect(self.database_path))
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT COUNT(DISTINCT user_id)
                FROM analytics_events
                WHERE date(timestamp) = date('now') AND user_id IS NOT NULL
            """
            )

            result = cursor.fetchone()[0] or 0
            conn.close()

            return result

        except Exception as e:
            logger.error(f"[ANALYTICS] Failed to count active users today: {e}")
            return 0

    def _analytics_worker(self):
        """Background analytics processing worker"""
        while self._running:
            try:
                time.sleep(3600)  # Run every hour

                # Calculate and cache key metrics
                for metric_id in self.metrics:
                    try:
                        self.calculate_metric(metric_id)
                    except Exception as e:
                        logger.error(
                            f"[ANALYTICS] Failed to calculate metric {metric_id}: {e}"
                        )

                logger.info("[ANALYTICS] Periodic metrics calculation completed")

            except Exception as e:
                logger.error(f"[ANALYTICS] Analytics worker error: {e}")
                time.sleep(3600)

    def _cleanup_worker(self):
        """Background cleanup worker"""
        while self._running:
            try:
                time.sleep(86400)  # Run daily

                # Clean old events
                cutoff_time = datetime.now() - timedelta(days=self.event_retention_days)

                conn = cast(ISyncConnection, sqlite3.connect(self.database_path))
                cursor = conn.cursor()

                cursor.execute(
                    "DELETE FROM analytics_events WHERE timestamp < ?",
                    (cutoff_time.isoformat(),),
                )

                # Clean old report executions
                cursor.execute(
                    "DELETE FROM report_executions WHERE execution_time < ?",
                    ((datetime.now() - timedelta(days=30)).isoformat(),),
                )

                conn.commit()
                conn.close()

                # Clean in-memory data
                with self._lock:
                    self.events = [e for e in self.events if e.timestamp >= cutoff_time]

                    # Clear old cache entries
                    self.cached_results.clear()

                logger.info("[ANALYTICS] Old analytics data cleaned up")

            except Exception as e:
                logger.error(f"[ANALYTICS] Cleanup worker error: {e}")
                time.sleep(86400)

    def shutdown(self):
        """Shutdown the analytics system"""
        self._running = False
        logger.info("[ANALYTICS] Analytics system shutdown")


# Global analytics instance
analytics_system = None


def get_analytics_system() -> EnterpriseAnalytics:
    """Get global analytics system instance"""
    global analytics_system

    if analytics_system is None:
        analytics_system = EnterpriseAnalytics()

    return analytics_system


def initialize_enterprise_analytics():
    """Initialize enterprise analytics system"""
    try:
        analytics = get_analytics_system()
        logger.info("[ANALYTICS] Enterprise analytics system initialized")
        return analytics
    except Exception as e:
        logger.error(f"[ANALYTICS] Failed to initialize analytics: {e}")
        return None


if __name__ == "__main__":
    # Test the analytics system
    analytics = initialize_enterprise_analytics()

    if analytics:
        # Track some test events
        analytics.track_event(
            "page_view", user_id="user123", properties={"page": "/dashboard"}
        )
        analytics.track_event(
            "api_request", properties={"response_time": 150, "endpoint": "/api/users"}
        )
        analytics.track_event(
            "conversion", user_id="user123", properties={"value": 100}
        )

        # Wait a bit for processing
        time.sleep(2)

        # Generate dashboard
        dashboard = analytics.get_analytics_dashboard()
        print(f"Analytics dashboard: {json.dumps(dashboard, indent=2, default=str)}")

        # Generate a report
        report = analytics.generate_report("daily_summary")
        print(f"Daily summary report: {json.dumps(report, indent=2, default=str)}")

        # Calculate a metric
        metric = analytics.calculate_metric("daily_active_users")
        print(f"DAU metric: {json.dumps(metric, indent=2, default=str)}")

        # Shutdown
        analytics.shutdown()
