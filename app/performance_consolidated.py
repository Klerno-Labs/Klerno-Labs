"""Klerno Labs - Consolidated Performance System
Enterprise-grade performance optimization and monitoring
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
from collections import OrderedDict, defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# =============================================================================
# Core Performance Models
# =============================================================================


@dataclass
class PerformanceMetrics:
    """Real-time performance metrics tracking."""

    endpoint: str
    method: str
    response_time_ms: float
    status_code: int
    timestamp: datetime
    user_agent: str | None = None
    remote_addr: str | None = None


@dataclass
class PerformanceMetric:
    """Performance metric data point."""

    timestamp: datetime
    operation: str
    duration_ms: float
    memory_mb: float
    cpu_percent: float
    metadata: dict[str, Any]


class CacheStrategy(str, Enum):
    """Cache strategy options."""

    LRU = "lru"
    LFU = "lfu"
    TTL = "ttl"
    ADAPTIVE = "adaptive"


# =============================================================================
# Advanced Caching System
# =============================================================================


class AdvancedCache:
    """High-performance caching with multiple strategies."""

    def __init__(
        self,
        max_size: int = 10000,
        strategy: CacheStrategy = CacheStrategy.LRU,
        default_ttl: int = 3600,
    ) -> None:
        self.max_size = max_size
        self.strategy = strategy
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._access_counts: dict[str, int] = defaultdict(int)
        self._timestamps: dict[str, datetime] = {}
        self._lock = threading.RLock()

        # Performance tracking
        self.hits = 0
        self.misses = 0
        self.evictions = 0

        # Internal cache serialization: pickle is used for performance and
        # is safe here as we control the data being cached

    def get(self, key: str) -> Any:
        """Get item from cache."""
        with self._lock:
            if key not in self._cache:
                self.misses += 1
                return None

            # Check TTL expiration
            if self._is_expired(key):
                del self._cache[key]
                self._access_counts.pop(key, None)
                self._timestamps.pop(key, None)
                self.misses += 1
                return None

            # Update access tracking
            self._access_counts[key] += 1

            # Move to end for LRU
            if self.strategy == CacheStrategy.LRU:
                self._cache.move_to_end(key)

            self.hits += 1
            return self._cache[key]

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set item in cache."""
        with self._lock:
            if key in self._cache:
                # Update existing
                self._cache[key] = value
                self._timestamps[key] = datetime.now(UTC)
                if self.strategy == CacheStrategy.LRU:
                    self._cache.move_to_end(key)
                return

            # Check if we need to evict
            if len(self._cache) >= self.max_size:
                self._evict()

            # Add new item
            self._cache[key] = value
            self._access_counts[key] = 1
            self._timestamps[key] = datetime.now(UTC)

    def _is_expired(self, key: str) -> bool:
        """Check if cache entry has expired."""
        if key not in self._timestamps:
            return True

        age = datetime.now(UTC) - self._timestamps[key]
        return age.total_seconds() > self.default_ttl

    def _evict(self) -> None:
        """Evict items based on strategy."""
        if not self._cache:
            return

        if self.strategy == CacheStrategy.LRU:
            # Remove least recently used (first item)
            key, _ = self._cache.popitem(last=False)
        elif self.strategy == CacheStrategy.LFU:
            # Remove least frequently used
            key = min(self._access_counts, key=lambda k: self._access_counts[k])
            del self._cache[key]
        else:  # TTL or ADAPTIVE
            # Remove oldest
            key = min(self._timestamps, key=lambda k: self._timestamps[k])
            del self._cache[key]

        # Clean up tracking data
        self._access_counts.pop(key, None)
        self._timestamps.pop(key, None)
        self.evictions += 1

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._access_counts.clear()
            self._timestamps.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get cache performance statistics."""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0

        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "hit_rate": hit_rate,
            "size": len(self._cache),
            "max_size": self.max_size,
        }


# =============================================================================
# Performance Profiler
# =============================================================================


class PerformanceProfiler:
    """Advanced performance profiler with detailed analytics."""

    def __init__(self, db_path: str = "./data/performance.db") -> None:
        self.db_path = db_path
        self.metrics: list[PerformanceMetric] = []
        self._buffer: deque[PerformanceMetric] = deque(maxlen=10000)
        self._lock = threading.Lock()

        # System monitoring
        self._system_metrics: dict[str, Any] = {}

        # Initialize database
        self._init_performance_database()

        # Start background monitoring
        self._start_system_monitoring()

    def _init_performance_database(self) -> None:
        """Initialize performance monitoring database."""
        import sqlite3
        from pathlib import Path

        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            # Performance metrics table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    duration_ms REAL NOT NULL,
                    memory_mb REAL NOT NULL,
                    cpu_percent REAL NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """,
            )

            # System metrics table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    cpu_percent REAL,
                    memory_percent REAL,
                    disk_usage_percent REAL,
                    network_sent_mb REAL,
                    network_recv_mb REAL,
                    active_connections INTEGER,
                    load_average REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """,
            )

            # Create indexes for performance
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_perf_operation ON performance_metrics(operation)",
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_perf_timestamp ON performance_metrics(timestamp)",
            )

    def _start_system_monitoring(self) -> None:
        """Start background system monitoring.

        In test environments (pytest), skip starting the background thread to
        avoid log noise and timing variability. Functional coverage is retained
        via unit tests on the public methods.
        """
        try:  # Skip under pytest to ensure quiet, deterministic test runs
            import sys as _sys

            if "pytest" in _sys.modules:
                return
        except Exception:
            pass

        def monitor() -> None:
            while True:
                try:
                    self._collect_system_metrics()
                    time.sleep(60)  # Collect every minute
                except Exception:
                    logger.debug("System monitoring error", exc_info=True)
                    time.sleep(60)

        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()

    def _collect_system_metrics(self) -> None:
        """Collect system performance metrics."""
        try:
            import psutil

            # CPU and memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            # Network stats
            net_io = psutil.net_io_counters()
            net_sent_mb = net_io.bytes_sent / (1024 * 1024)
            net_recv_mb = net_io.bytes_recv / (1024 * 1024)

            # Process count
            active_connections = len(psutil.pids())

            # Load average (Unix-like systems)
            try:
                # os.getloadavg() is Unix-only, not available on Windows
                load_avg = getattr(os, "getloadavg", lambda: [0.0])()[0]
            except (AttributeError, OSError):
                load_avg = 0.0

            self._system_metrics = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_usage_percent": disk.percent,
                "network_sent_mb": net_sent_mb,
                "network_recv_mb": net_recv_mb,
                "active_connections": active_connections,
                "load_average": load_avg,
                "timestamp": datetime.now(UTC).isoformat(),
            }

        except ImportError:
            # psutil not available
            self._system_metrics = {
                "cpu_percent": 0.0,
                "memory_percent": 0.0,
                "timestamp": datetime.now(UTC).isoformat(),
            }

    def record_metric(
        self,
        operation: str,
        duration_ms: float,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record a performance metric."""
        try:
            import psutil

            memory_mb = psutil.Process().memory_info().rss / (1024 * 1024)
            cpu_percent = psutil.Process().cpu_percent()
        except ImportError:
            memory_mb = 0.0
            cpu_percent = 0.0

        metric = PerformanceMetric(
            timestamp=datetime.now(UTC),
            operation=operation,
            duration_ms=duration_ms,
            memory_mb=memory_mb,
            cpu_percent=cpu_percent,
            metadata=metadata or {},
        )

        with self._lock:
            self._buffer.append(metric)

        # Async persist to database
        asyncio.create_task(self._persist_metric(metric))

    async def _persist_metric(self, metric: PerformanceMetric) -> None:
        """Persist metric to database."""
        try:
            import sqlite3

            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO performance_metrics
                    (timestamp, operation, duration_ms, memory_mb, cpu_percent, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        metric.timestamp.isoformat(),
                        metric.operation,
                        metric.duration_ms,
                        metric.memory_mb,
                        metric.cpu_percent,
                        json.dumps(metric.metadata),
                    ),
                )
        except Exception as e:
            logger.error(f"Failed to persist metric: {e}")

    def get_metrics_summary(self, hours: int = 24) -> dict[str, Any]:
        """Get performance metrics summary."""
        cutoff = datetime.now(UTC) - timedelta(hours=hours)

        with self._lock:
            recent_metrics = [m for m in self._buffer if m.timestamp >= cutoff]

        if not recent_metrics:
            return {"message": "No metrics available"}

        # Calculate statistics
        durations = [m.duration_ms for m in recent_metrics]
        memory_usage = [m.memory_mb for m in recent_metrics]

        return {
            "period_hours": hours,
            "total_operations": len(recent_metrics),
            "avg_duration_ms": sum(durations) / len(durations),
            "max_duration_ms": max(durations),
            "min_duration_ms": min(durations),
            "avg_memory_mb": sum(memory_usage) / len(memory_usage),
            "max_memory_mb": max(memory_usage),
            "system_metrics": self._system_metrics,
            "top_operations": self._get_top_operations(recent_metrics),
        }

    def _get_top_operations(self, metrics: list[PerformanceMetric]) -> dict[str, Any]:
        """Get top operations by frequency and duration."""
        operation_stats: dict[str, list[float]] = defaultdict(list[Any])

        for metric in metrics:
            operation_stats[metric.operation].append(metric.duration_ms)

        top_by_frequency = sorted(
            operation_stats.items(),
            key=lambda x: len(x[1]),
            reverse=True,
        )[:10]

        top_by_duration = sorted(
            operation_stats.items(),
            key=lambda x: sum(x[1]) / len(x[1]),
            reverse=True,
        )[:10]

        return {
            "by_frequency": [
                {"operation": op, "count": len(durations)}
                for op, durations in top_by_frequency
            ],
            "by_avg_duration": [
                {"operation": op, "avg_duration_ms": sum(durations) / len(durations)}
                for op, durations in top_by_duration
            ],
        }


# =============================================================================
# Performance Middleware
# =============================================================================


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic performance tracking."""

    def __init__(self, app, profiler: PerformanceProfiler) -> None:
        super().__init__(app)
        self.profiler = profiler

    async def dispatch(self, request: Request, call_next) -> Any:
        """Track request performance."""
        start_time = time.time()

        response = await call_next(request)

        duration_ms = (time.time() - start_time) * 1000

        # Record performance metric
        self.profiler.record_metric(
            operation=f"{request.method} {request.url.path}",
            duration_ms=duration_ms,
            metadata={
                "status_code": response.status_code,
                "user_agent": request.headers.get("user-agent"),
                "remote_addr": request.client.host if request.client else None,
            },
        )

        # Add performance headers
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

        return response


# =============================================================================
# Performance Decorators
# =============================================================================


# =============================================================================
# Performance Decorators
# =============================================================================


def cached(ttl: int = 3600, max_size: int = 1000) -> None:
    """Decorator to cache function results."""

    def decorator(func: Callable) -> Callable:
        cache = AdvancedCache(max_size=max_size, default_ttl=ttl)

        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                # Create cache key from args and kwargs
                key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"

                # Try to get from cache
                result = cache.get(key)
                if result is not None:
                    return result

                # Execute function and cache result
                result = await func(*args, **kwargs)
                cache.set(key, result)
                return result

            # Attach cache for inspection using setattr
            async_wrapper._cache = cache
            return async_wrapper

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> None:
            # Create cache key from args and kwargs
            key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"

            # Try to get from cache
            result = cache.get(key)
            if result is not None:
                return result

            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(key, result)
            return result

        # Attach cache for inspection using setattr
        sync_wrapper._cache = cache
        return sync_wrapper

    return decorator


def track_performance(operation_name: str | None = None) -> None:
    """Decorator to track function performance."""

    def decorator(func: Callable) -> Callable:
        op_name = operation_name or f"{func.__module__}.{func.__name__}"

        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    duration_ms = (time.time() - start_time) * 1000
                    # Global profiler would be injected here
                    logger.debug(f"Performance: {op_name} took {duration_ms:.2f}ms")

            return async_wrapper

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> None:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration_ms = (time.time() - start_time) * 1000
                logger.debug(f"Performance: {op_name} took {duration_ms:.2f}ms")

        return sync_wrapper

    return decorator


# =============================================================================
# Global Performance Manager
# =============================================================================


class PerformanceManager:
    """Centralized performance management."""

    def __init__(self) -> None:
        self.profiler = PerformanceProfiler()
        self.cache = AdvancedCache()
        self._enabled = True

    def enable(self) -> None:
        """Enable performance tracking."""
        self._enabled = True

    def disable(self) -> None:
        """Disable performance tracking."""
        self._enabled = False

    def get_middleware(self) -> PerformanceMiddleware:
        """Get performance middleware."""
        return PerformanceMiddleware(None, self.profiler)

    def get_summary(self) -> dict[str, Any]:
        """Get comprehensive performance summary."""
        return {
            "profiler": self.profiler.get_metrics_summary(),
            "cache": self.cache.get_stats(),
            "enabled": self._enabled,
        }


# Global instance
performance_manager = PerformanceManager()
