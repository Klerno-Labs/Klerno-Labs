"""
Advanced Performance Monitoring & Analytics for Klerno Labs
Real-time performance tracking, user analytics, and regression detection
"""

import asyncio
import statistics
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
from typing import Any, Deque

import psutil
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class PerformanceMetric:
    name: str
    value: float
    timestamp: float
    labels: dict[str, str]
    metric_type: MetricType


@dataclass
class UserSession:
    session_id: str
    ip: str
    user_agent: str
    start_time: float
    last_activity: float
    page_views: int
    actions: list[str]
    conversion_events: list[str]


class PerformanceTracker:
    """Advanced performance metrics tracking"""

    def __init__(self):
        self.metrics: list[PerformanceMetric] = []
        self.request_times: Deque[float] = deque(maxlen=1000)  # Last 1000 requests
        self.error_rates: dict[str, int] = defaultdict(int)
        self.endpoint_stats: dict[str, list[float]] = defaultdict(list)
        self.system_metrics: dict[str, Any] = {}

    def record_metric(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
        metric_type: MetricType = MetricType.GAUGE,
    ):
        """Record a performance metric"""
        metric = PerformanceMetric(
            name=name,
            value=value,
            timestamp=time.time(),
            labels=labels or {},
            metric_type=metric_type,
        )
        self.metrics.append(metric)

        # Keep only last 10000 metrics to prevent memory issues
        if len(self.metrics) > 10000:
            self.metrics = self.metrics[-5000:]

    def record_request(
        self, method: str, path: str, status_code: int, duration: float, size: int = 0
    ):
        """Record request performance data"""
        self.request_times.append(duration)
        self.endpoint_stats[f"{method} {path}"].append(duration)

        # Record metrics
        self.record_metric(
            "http_requests_total",
            1,
            {"method": method, "path": path, "status": str(status_code)},
            MetricType.COUNTER,
        )

        self.record_metric(
            "http_request_duration",
            duration,
            {"method": method, "path": path},
            MetricType.HISTOGRAM,
        )

        if size > 0:
            self.record_metric(
                "http_response_size",
                size,
                {"method": method, "path": path},
                MetricType.HISTOGRAM,
            )

        # Track errors
        if status_code >= 400:
            self.error_rates[f"{method} {path}"] += 1

    def get_performance_summary(self) -> dict[str, Any]:
        """Get comprehensive performance summary"""
        now = time.time()

        # Request performance
        if self.request_times:
            avg_response_time = statistics.mean(self.request_times)
            p95_response_time = statistics.quantiles(self.request_times, n=20)[
                18
            ]  # 95th percentile
            p99_response_time = statistics.quantiles(self.request_times, n=100)[
                98
            ]  # 99th percentile
        else:
            avg_response_time = p95_response_time = p99_response_time = 0

        # System metrics
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
        except Exception:
            cpu_percent = 0
            memory = None
            disk = None

        return {
            "timestamp": now,
            "request_performance": {
                "total_requests": len(self.request_times),
                "avg_response_time": avg_response_time,
                "p95_response_time": p95_response_time,
                "p99_response_time": p99_response_time,
                "requests_per_minute": (
                    len([t for t in self.request_times if now - t < 60])
                    if self.request_times
                    else 0
                ),
            },
            "system_performance": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent if memory else 0,
                "memory_used_gb": memory.used / (1024**3) if memory else 0,
                "disk_percent": disk.percent if disk else 0,
                "disk_free_gb": disk.free / (1024**3) if disk else 0,
            },
            "error_rates": dict(self.error_rates),
            "endpoint_stats": {
                endpoint: {
                    "count": len(times),
                    "avg_time": statistics.mean(times),
                    "max_time": max(times),
                    "min_time": min(times),
                }
                for endpoint, times in self.endpoint_stats.items()
                if times
            },
        }


class UserAnalytics:
    """User behavior and conversion analytics"""

    def __init__(self):
        self.active_sessions: dict[str, UserSession] = {}
        self.conversion_funnels = defaultdict(list)
        self.page_analytics = defaultdict(int)
        self.user_flows = defaultdict(list)

    def start_session(self, session_id: str, ip: str, user_agent: str):
        """Start a new user session"""
        self.active_sessions[session_id] = UserSession(
            session_id=session_id,
            ip=ip,
            user_agent=user_agent,
            start_time=time.time(),
            last_activity=time.time(),
            page_views=0,
            actions=[],
            conversion_events=[],
        )

    def track_page_view(self, session_id: str, path: str):
        """Track a page view"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session.page_views += 1
            session.last_activity = time.time()
            session.actions.append(f"page_view:{path}")

            self.page_analytics[path] += 1
            self.user_flows[session_id].append(path)

    def track_conversion(self, session_id: str, event: str):
        """Track a conversion event"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session.conversion_events.append(event)
            session.last_activity = time.time()

            self.conversion_funnels[event].append(
                {
                    "session_id": session_id,
                    "timestamp": time.time(),
                    "pages_visited": session.page_views,
                }
            )

    def get_analytics_summary(self) -> dict[str, Any]:
        """Get user analytics summary"""
        now = time.time()
        active_sessions = [
            s for s in self.active_sessions.values() if now - s.last_activity < 1800
        ]  # Active in last 30 minutes

        return {
            "timestamp": now,
            "active_sessions": len(active_sessions),
            "total_sessions": len(self.active_sessions),
            "avg_session_duration": (
                statistics.mean(
                    [
                        s.last_activity - s.start_time
                        for s in self.active_sessions.values()
                    ]
                )
                if self.active_sessions
                else 0
            ),
            "page_views": dict(self.page_analytics),
            "conversion_rates": {
                event: len(conversions)
                for event, conversions in self.conversion_funnels.items()
            },
            "popular_flows": self._get_popular_flows(),
        }

    def _get_popular_flows(self) -> list[dict[str, Any]]:
        """Get most popular user flows"""
        flow_counts: defaultdict[str, int] = defaultdict(int)

        for flow in self.user_flows.values():
            if len(flow) >= 2:
                # Track 2-page flows
                for i in range(len(flow) - 1):
                    flow_pattern = f"{flow[i]} -> {flow[i + 1]}"
                    flow_counts[flow_pattern] += 1

        return [
            {"flow": flow, "count": count}
            for flow, count in sorted(
                flow_counts.items(), key=lambda x: x[1], reverse=True
            )[:10]
        ]


class RegressionDetector:
    """Automated performance regression detection"""

    def __init__(self):
        self.baseline_metrics: dict[str, Any] = {}
        self.alerts: list[dict[str, Any]] = []
        self.thresholds = {
            "response_time_increase": 0.5,  # 50% increase
            "error_rate_increase": 0.1,  # 10% increase
            "cpu_threshold": 80,  # 80% CPU
            "memory_threshold": 85,  # 85% memory
        }

    def update_baseline(self, metrics: dict[str, Any]):
        """Update performance baseline"""
        self.baseline_metrics = {
            "avg_response_time": metrics["request_performance"]["avg_response_time"],
            "error_rate": len(metrics["error_rates"]),
            "cpu_percent": metrics["system_performance"]["cpu_percent"],
            "memory_percent": metrics["system_performance"]["memory_percent"],
            "timestamp": metrics["timestamp"],
        }

    def check_regressions(
        self, current_metrics: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Check for performance regressions"""
        alerts: list[dict[str, Any]] = []

        if not self.baseline_metrics:
            return alerts

        current = current_metrics
        baseline = self.baseline_metrics

        # Response time regression
        current_response_time = current["request_performance"]["avg_response_time"]
        baseline_response_time = baseline["avg_response_time"]

        if baseline_response_time > 0:
            response_time_increase = (
                current_response_time - baseline_response_time
            ) / baseline_response_time
            if response_time_increase > self.thresholds["response_time_increase"]:
                alerts.append(
                    {
                        "type": "response_time_regression",
                        "severity": "high",
                        "message": f"Response time increased by {response_time_increase:.1%}",
                        "current": current_response_time,
                        "baseline": baseline_response_time,
                    }
                )

        # CPU threshold
        current_cpu = current["system_performance"]["cpu_percent"]
        if current_cpu > self.thresholds["cpu_threshold"]:
            alerts.append(
                {
                    "type": "high_cpu",
                    "severity": "warning",
                    "message": f"CPU usage at {current_cpu:.1f}%",
                    "current": current_cpu,
                    "threshold": self.thresholds["cpu_threshold"],
                }
            )

        # Memory threshold
        current_memory = current["system_performance"]["memory_percent"]
        if current_memory > self.thresholds["memory_threshold"]:
            alerts.append(
                {
                    "type": "high_memory",
                    "severity": "warning",
                    "message": f"Memory usage at {current_memory:.1f}%",
                    "current": current_memory,
                    "threshold": self.thresholds["memory_threshold"],
                }
            )

        self.alerts.extend(alerts)
        return alerts


class AdvancedMonitoringMiddleware(BaseHTTPMiddleware):
    """Comprehensive monitoring middleware"""

    def __init__(self, app, start_background: bool = False):
        super().__init__(app)
        self.performance_tracker = PerformanceTracker()
        self.user_analytics = UserAnalytics()
        self.regression_detector = RegressionDetector()

        # Start background monitoring task only if explicitly requested
        if start_background:
            asyncio.create_task(self._background_monitoring())

    async def dispatch(self, request: Request, call_next):
        """Main monitoring dispatch"""
        start_time = time.time()

        # Extract session info
        session_id = request.cookies.get("session_id", "anonymous")
        ip = request.client.host if request.client else "127.0.0.1"
        user_agent = request.headers.get("user-agent", "")

        # Start session if new
        if session_id not in self.user_analytics.active_sessions:
            self.user_analytics.start_session(session_id, ip, user_agent)

        # Track page view for HTML requests
        if request.headers.get("accept", "").startswith("text/html"):
            self.user_analytics.track_page_view(session_id, request.url.path)

        # Process request
        response = await call_next(request)

        # Record performance metrics
        duration = time.time() - start_time
        response_size = len(response.body) if hasattr(response, "body") else 0

        self.performance_tracker.record_request(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration=duration,
            size=response_size,
        )

        # Add monitoring headers
        response.headers["X-Response-Time"] = f"{duration:.3f}s"
        response.headers["X-Monitoring-ID"] = session_id

        # Track conversions based on response
        if response.status_code == 200:
            if request.url.path == "/auth/login":
                self.user_analytics.track_conversion(session_id, "login")
            elif request.url.path == "/auth/signup":
                self.user_analytics.track_conversion(session_id, "signup")
            elif request.url.path.startswith("/dashboard"):
                self.user_analytics.track_conversion(session_id, "dashboard_access")

        return response

    async def _background_monitoring(self):
        """Background task for monitoring and alerting"""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute

                # Get current metrics
                performance_summary = self.performance_tracker.get_performance_summary()
                self.user_analytics.get_analytics_summary()

                # Check for regressions
                alerts = self.regression_detector.check_regressions(performance_summary)

                if alerts:
                    print("🚨 Performance Alerts:")
                    for alert in alerts:
                        print(f"  {alert['severity'].upper()}: {alert['message']}")

                # Update baseline every hour
                if not hasattr(self, "_last_baseline_update"):
                    self._last_baseline_update = time.time()

                if time.time() - self._last_baseline_update > 3600:  # 1 hour
                    self.regression_detector.update_baseline(performance_summary)
                    self._last_baseline_update = time.time()
                    print("[MONITOR] Performance baseline updated")

            except Exception as e:
                print(f"Monitoring error: {e}")

    def get_monitoring_dashboard(self) -> dict[str, Any]:
        """Get comprehensive monitoring dashboard data"""
        return {
            "performance": self.performance_tracker.get_performance_summary(),
            "analytics": self.user_analytics.get_analytics_summary(),
            "alerts": self.regression_detector.alerts[-50:],  # Last 50 alerts
            "health_status": self._get_health_status(),
        }

    def _get_health_status(self) -> str:
        """Get overall system health status"""
        performance = self.performance_tracker.get_performance_summary()

        # Check various health indicators
        response_time = performance["request_performance"]["avg_response_time"]
        cpu_percent = performance["system_performance"]["cpu_percent"]
        memory_percent = performance["system_performance"]["memory_percent"]
        error_count = len(performance["error_rates"])

        if (
            response_time > 2.0
            or cpu_percent > 90
            or memory_percent > 95
            or error_count > 10
        ):
            return "critical"
        elif (
            response_time > 1.0
            or cpu_percent > 70
            or memory_percent > 80
            or error_count > 5
        ):
            return "warning"
        else:
            return "healthy"


# Global monitoring instance
monitoring_middleware = None


def get_monitoring_middleware(start_background: bool = False):
    """Get or create monitoring middleware instance.

    By default the background monitoring loop is not started. Pass
    `start_background=True` when running in production to enable the
    periodic monitoring task.
    """
    global monitoring_middleware
    if not monitoring_middleware:
        monitoring_middleware = AdvancedMonitoringMiddleware(
            None, start_background=start_background
        )
    return monitoring_middleware
