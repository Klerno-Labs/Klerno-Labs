import statistics
import threading
import time
from collections import defaultdict, deque


class PerformanceMonitor:
    """Real-time performance monitoring."""

    def __init__(self, window_size: int = 1000) -> None:
        self.window_size = window_size
        self.metrics = defaultdict(lambda: deque(maxlen=window_size))
        self.lock = threading.Lock()

    def record_response_time(self, endpoint: str, response_time_ms: float) -> None:
        """Record response time for an endpoint."""
        with self.lock:
            self.metrics[f"{endpoint}_response_time"].append(response_time_ms)

    def record_database_query_time(self, query_type: str, time_ms: float) -> None:
        """Record database query execution time."""
        with self.lock:
            self.metrics[f"db_{query_type}_time"].append(time_ms)

    def get_stats(self, metric_name: str) -> dict[str, float]:
        """Get statistics for a metric."""
        with self.lock:
            values = list(self.metrics[metric_name])

        if not values:
            return {}

        return {
            "count": len(values),
            "avg": statistics.mean(values),
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values),
            "p95": sorted(values)[int(len(values) * 0.95)] if len(values) > 0 else 0,
        }

    def get_all_stats(self) -> dict[str, dict[str, float]]:
        """Get statistics for all metrics."""
        return {metric: self.get_stats(metric) for metric in self.metrics}


# Global monitor instance
perf_monitor = PerformanceMonitor()


def timed_endpoint(endpoint_name: str):
    """Decorator to automatically time endpoint execution."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                end_time = time.perf_counter()
                response_time_ms = (end_time - start_time) * 1000
                perf_monitor.record_response_time(endpoint_name, response_time_ms)

        return wrapper

    return decorator


# Usage:
# @timed_endpoint("health_check")
# def health_endpoint():
#     return {"status": "ok"}
