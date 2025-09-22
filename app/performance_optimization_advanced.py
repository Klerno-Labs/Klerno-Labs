"""
Klerno Labs - Advanced Performance Optimization
Enterprise-grade performance optimization for 0.01% quality applications
"""

import asyncio
import functools
import gzip
import hashlib
import json
import logging
import pickle
import sqlite3
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import psutil

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Performance metric data point."""

    timestamp: datetime
    operation: str
    duration_ms: float
    memory_used_mb: float
    cpu_percent: float
    status: str  # success, error, timeout
    details: dict[str, Any]


@dataclass
class CacheEntry:
    """Cache entry with metadata."""

    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int
    ttl_seconds: int | None = None
    size_bytes: int = 0


class AdvancedCache:
    """Multi-tier cache with intelligent eviction and compression."""

    def __init__(self, max_size_mb: int = 100, compression_threshold: int = 1024):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.compression_threshold = compression_threshold
        self.cache: dict[str, CacheEntry] = {}
        self.access_order = deque()  # LRU tracking
        self.current_size_bytes = 0
        self.hit_count = 0
        self.miss_count = 0
        self.eviction_count = 0
        self._lock = threading.RLock()

        # Performance tracking
        self.get_times = deque(maxlen=1000)
        self.set_times = deque(maxlen=1000)

    def _serialize_value(self, value: Any) -> bytes:
        """Serialize and optionally compress value."""
        serialized = pickle.dumps(value)

        if len(serialized) > self.compression_threshold:
            serialized = gzip.compress(serialized)

        return serialized

    def _deserialize_value(self, data: bytes) -> Any:
        """Deserialize and decompress value."""
        try:
            # Try decompression first
            decompressed = gzip.decompress(data)
            return pickle.loads(decompressed)
        except Exception:
            # If decompression fails, try direct pickle
            return pickle.loads(data)

    def _calculate_size(self, value: Any) -> int:
        """Calculate approximate size of value in bytes."""
        try:
            return len(self._serialize_value(value))
        except Exception:
            return 1024  # Default size if calculation fails

    def _evict_lru(self) -> None:
        """Evict least recently used entries."""
        while self.current_size_bytes > self.max_size_bytes and self.access_order:
            lru_key = self.access_order.popleft()
            if lru_key in self.cache:
                entry = self.cache.pop(lru_key)
                self.current_size_bytes -= entry.size_bytes
                self.eviction_count += 1

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache."""
        start_time = time.time()

        with self._lock:
            if key in self.cache:
                entry = self.cache[key]

                # Check TTL
                if entry.ttl_seconds:
                    age = (datetime.now() - entry.created_at).total_seconds()
                    if age > entry.ttl_seconds:
                        self.delete(key)
                        self.miss_count += 1
                        self.get_times.append((time.time() - start_time) * 1000)
                        return default

                # Update access info
                entry.last_accessed = datetime.now()
                entry.access_count += 1

                # Move to end of access order (most recent)
                if key in self.access_order:
                    self.access_order.remove(key)
                self.access_order.append(key)

                self.hit_count += 1
                self.get_times.append((time.time() - start_time) * 1000)

                try:
                    return self._deserialize_value(entry.value)
                except Exception:
                    # If deserialization fails, remove entry
                    self.delete(key)
                    self.miss_count += 1
                    return default

            self.miss_count += 1
            self.get_times.append((time.time() - start_time) * 1000)
            return default

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> bool:
        """Set value in cache."""
        start_time = time.time()

        try:
            with self._lock:
                # Remove existing entry if present
                if key in self.cache:
                    old_entry = self.cache[key]
                    self.current_size_bytes -= old_entry.size_bytes
                    if key in self.access_order:
                        self.access_order.remove(key)

                # Serialize value
                serialized_value = self._serialize_value(value)
                size_bytes = len(serialized_value)

                # Check if value is too large
                if size_bytes > self.max_size_bytes:
                    logger.warning(f"Cache value too large: {size_bytes} bytes")
                    self.set_times.append((time.time() - start_time) * 1000)
                    return False

                # Create new entry
                entry = CacheEntry(
                    key=key,
                    value=serialized_value,
                    created_at=datetime.now(),
                    last_accessed=datetime.now(),
                    access_count=0,
                    ttl_seconds=ttl_seconds,
                    size_bytes=size_bytes,
                )

                # Add to cache
                self.cache[key] = entry
                self.access_order.append(key)
                self.current_size_bytes += size_bytes

                # Evict if necessary
                self._evict_lru()

                self.set_times.append((time.time() - start_time) * 1000)
                return True

        except Exception as e:
            logger.error(f"Cache set error: {e}")
            self.set_times.append((time.time() - start_time) * 1000)
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        with self._lock:
            if key in self.cache:
                entry = self.cache.pop(key)
                self.current_size_bytes -= entry.size_bytes
                if key in self.access_order:
                    self.access_order.remove(key)
                return True
            return False

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self.cache.clear()
            self.access_order.clear()
            self.current_size_bytes = 0

    def get_stats(self) -> dict[str, Any]:
        """Get cache performance statistics."""
        total_requests = self.hit_count + self.miss_count
        hit_rate = (self.hit_count / total_requests * 100) if total_requests > 0 else 0

        avg_get_time = (
            sum(self.get_times) / len(self.get_times) if self.get_times else 0
        )
        avg_set_time = (
            sum(self.set_times) / len(self.set_times) if self.set_times else 0
        )

        return {
            "entries": len(self.cache),
            "size_mb": self.current_size_bytes / 1024 / 1024,
            "max_size_mb": self.max_size_bytes / 1024 / 1024,
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "hit_rate_percent": hit_rate,
            "eviction_count": self.eviction_count,
            "avg_get_time_ms": avg_get_time,
            "avg_set_time_ms": avg_set_time,
        }


class PerformanceProfiler:
    """Advanced performance profiler with detailed analytics."""

    def __init__(self, db_path: str = "./data/performance.db"):
        self.db_path = db_path
        self.metrics: list[PerformanceMetric] = []
        self.operation_times: dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.slow_query_threshold_ms = 1000
        self.memory_samples = deque(maxlen=100)
        self.cpu_samples = deque(maxlen=100)

        # Initialize database
        self._init_performance_database()

        # Start background monitoring
        self._start_system_monitoring()

    def _init_performance_database(self) -> None:
        """Initialize performance monitoring database."""
        Path(self.db_path).parent.mkdir(exist_ok=True, parents=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Performance metrics table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                operation TEXT NOT NULL,
                duration_ms REAL NOT NULL,
                memory_used_mb REAL,
                cpu_percent REAL,
                status TEXT NOT NULL,
                details TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # System metrics table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                cpu_percent REAL,
                memory_percent REAL,
                memory_available_mb REAL,
                disk_io_read_mb REAL,
                disk_io_write_mb REAL,
                network_bytes_sent REAL,
                network_bytes_recv REAL,
                active_connections INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Create indexes
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_perf_operation ON performance_metrics(operation)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_perf_timestamp ON performance_metrics(timestamp)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_sys_timestamp ON system_metrics(timestamp)"
        )

        conn.commit()
        conn.close()

        logger.info("✅ Performance database initialized")

    def _start_system_monitoring(self) -> None:
        """Start background system monitoring."""

        def monitor_system():
            while True:
                try:
                    # Collect system metrics
                    cpu_percent = psutil.cpu_percent(interval=1)
                    memory = psutil.virtual_memory()
                    disk_io = psutil.disk_io_counters()
                    network_io = psutil.net_io_counters()

                    self.cpu_samples.append(cpu_percent)
                    self.memory_samples.append(memory.percent)

                    # Log to database periodically
                    now = datetime.now()
                    if now.second % 30 == 0:  # Every 30 seconds
                        self._log_system_metrics(
                            {
                                "timestamp": now,
                                "cpu_percent": cpu_percent,
                                "memory_percent": memory.percent,
                                "memory_available_mb": memory.available / 1024 / 1024,
                                "disk_io_read_mb": (
                                    disk_io.read_bytes / 1024 / 1024 if disk_io else 0
                                ),
                                "disk_io_write_mb": (
                                    disk_io.write_bytes / 1024 / 1024 if disk_io else 0
                                ),
                                "network_bytes_sent": (
                                    network_io.bytes_sent if network_io else 0
                                ),
                                "network_bytes_recv": (
                                    network_io.bytes_recv if network_io else 0
                                ),
                            }
                        )

                    time.sleep(5)

                except Exception as e:
                    logger.error(f"System monitoring error: {e}")
                    time.sleep(10)

        # Start monitoring thread
        monitor_thread = threading.Thread(target=monitor_system, daemon=True)
        monitor_thread.start()

    def _log_system_metrics(self, metrics: dict[str, Any]) -> None:
        """Log system metrics to database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO system_metrics
                (timestamp, cpu_percent, memory_percent, memory_available_mb,
                 disk_io_read_mb, disk_io_write_mb, network_bytes_sent, network_bytes_recv)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    metrics["timestamp"].isoformat(),
                    metrics["cpu_percent"],
                    metrics["memory_percent"],
                    metrics["memory_available_mb"],
                    metrics["disk_io_read_mb"],
                    metrics["disk_io_write_mb"],
                    metrics["network_bytes_sent"],
                    metrics["network_bytes_recv"],
                ),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Error logging system metrics: {e}")

    def measure_performance(self, operation: str):
        """Decorator to measure function performance."""

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                start_memory = psutil.Process().memory_info().rss / 1024 / 1024
                start_cpu = psutil.Process().cpu_percent()

                status = "success"
                error_details = {}

                try:
                    if asyncio.iscoroutinefunction(func):
                        result = await func(*args, **kwargs)
                    else:
                        result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    status = "error"
                    error_details = {"error": str(e), "type": type(e).__name__}
                    raise
                finally:
                    end_time = time.time()
                    end_memory = psutil.Process().memory_info().rss / 1024 / 1024
                    end_cpu = psutil.Process().cpu_percent()

                    duration_ms = (end_time - start_time) * 1000
                    memory_used = end_memory - start_memory
                    cpu_used = end_cpu - start_cpu

                    # Record metric
                    metric = PerformanceMetric(
                        timestamp=datetime.now(),
                        operation=operation,
                        duration_ms=duration_ms,
                        memory_used_mb=memory_used,
                        cpu_percent=cpu_used,
                        status=status,
                        details=error_details,
                    )

                    self.record_metric(metric)

                    # Log slow operations
                    if duration_ms > self.slow_query_threshold_ms:
                        logger.warning(
                            f"🐌 Slow operation: {operation} took {duration_ms:.2f}ms"
                        )

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                start_memory = psutil.Process().memory_info().rss / 1024 / 1024

                status = "success"
                error_details = {}

                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    status = "error"
                    error_details = {"error": str(e), "type": type(e).__name__}
                    raise
                finally:
                    end_time = time.time()
                    end_memory = psutil.Process().memory_info().rss / 1024 / 1024

                    duration_ms = (end_time - start_time) * 1000
                    memory_used = end_memory - start_memory

                    # Record metric
                    metric = PerformanceMetric(
                        timestamp=datetime.now(),
                        operation=operation,
                        duration_ms=duration_ms,
                        memory_used_mb=memory_used,
                        cpu_percent=0,  # CPU tracking less accurate for sync functions
                        status=status,
                        details=error_details,
                    )

                    self.record_metric(metric)

                    # Log slow operations
                    if duration_ms > self.slow_query_threshold_ms:
                        logger.warning(
                            f"🐌 Slow operation: {operation} took {duration_ms:.2f}ms"
                        )

            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

        return decorator

    def record_metric(self, metric: PerformanceMetric) -> None:
        """Record a performance metric."""
        self.metrics.append(metric)
        self.operation_times[metric.operation].append(metric.duration_ms)

        # Log to database periodically
        if len(self.metrics) % 100 == 0:
            self._flush_metrics()

    def _flush_metrics(self) -> None:
        """Flush metrics to database."""
        if not self.metrics:
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            for metric in self.metrics:
                cursor.execute(
                    """
                    INSERT INTO performance_metrics
                    (timestamp, operation, duration_ms, memory_used_mb, cpu_percent, status, details)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        metric.timestamp.isoformat(),
                        metric.operation,
                        metric.duration_ms,
                        metric.memory_used_mb,
                        metric.cpu_percent,
                        metric.status,
                        json.dumps(metric.details),
                    ),
                )

            conn.commit()
            conn.close()

            logger.debug(f"Flushed {len(self.metrics)} performance metrics")
            self.metrics.clear()

        except Exception as e:
            logger.error(f"Error flushing performance metrics: {e}")

    def get_performance_summary(self, hours: int = 1) -> dict[str, Any]:
        """Get performance summary for the last N hours."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            since = datetime.now() - timedelta(hours=hours)

            # Get operation performance summary
            cursor.execute(
                """
                SELECT operation,
                       COUNT(*) as count,
                       AVG(duration_ms) as avg_duration,
                       MIN(duration_ms) as min_duration,
                       MAX(duration_ms) as max_duration,
                       AVG(memory_used_mb) as avg_memory,
                       SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error_count
                FROM performance_metrics
                WHERE timestamp >= ?
                GROUP BY operation
                ORDER BY avg_duration DESC
            """,
                (since.isoformat(),),
            )

            operations = []
            for row in cursor.fetchall():
                operations.append(
                    {
                        "operation": row[0],
                        "count": row[1],
                        "avg_duration_ms": round(row[2], 2),
                        "min_duration_ms": round(row[3], 2),
                        "max_duration_ms": round(row[4], 2),
                        "avg_memory_mb": round(row[5], 2) if row[5] else 0,
                        "error_count": row[6],
                        "error_rate_percent": (
                            round((row[6] / row[1]) * 100, 2) if row[1] > 0 else 0
                        ),
                    }
                )

            # Get system performance summary
            cursor.execute(
                """
                SELECT AVG(cpu_percent) as avg_cpu,
                       MAX(cpu_percent) as max_cpu,
                       AVG(memory_percent) as avg_memory,
                       MAX(memory_percent) as max_memory,
                       AVG(memory_available_mb) as avg_available_memory
                FROM system_metrics
                WHERE timestamp >= ?
            """,
                (since.isoformat(),),
            )

            system_row = cursor.fetchone()
            system_summary = {
                "avg_cpu_percent": round(system_row[0], 2) if system_row[0] else 0,
                "max_cpu_percent": round(system_row[1], 2) if system_row[1] else 0,
                "avg_memory_percent": round(system_row[2], 2) if system_row[2] else 0,
                "max_memory_percent": round(system_row[3], 2) if system_row[3] else 0,
                "avg_available_memory_mb": (
                    round(system_row[4], 2) if system_row[4] else 0
                ),
            }

            # Get slowest operations
            cursor.execute(
                """
                SELECT operation, duration_ms, timestamp
                FROM performance_metrics
                WHERE timestamp >= ? AND duration_ms > ?
                ORDER BY duration_ms DESC
                LIMIT 10
            """,
                (since.isoformat(), self.slow_query_threshold_ms),
            )

            slow_operations = []
            for row in cursor.fetchall():
                slow_operations.append(
                    {
                        "operation": row[0],
                        "duration_ms": round(row[1], 2),
                        "timestamp": row[2],
                    }
                )

            conn.close()

            return {
                "timestamp": datetime.now().isoformat(),
                "summary_period_hours": hours,
                "operations": operations,
                "system_summary": system_summary,
                "slow_operations": slow_operations,
                "current_memory_samples": list(self.memory_samples)[-10:],
                "current_cpu_samples": list(self.cpu_samples)[-10:],
            }

        except Exception as e:
            logger.error(f"Error getting performance summary: {e}")
            return {"error": str(e)}


# Global instances
cache = AdvancedCache(max_size_mb=100)
profiler = PerformanceProfiler()


def get_cache() -> AdvancedCache:
    """Get the global cache instance."""
    return cache


def get_profiler() -> PerformanceProfiler:
    """Get the global profiler instance."""
    return profiler


# Decorators for easy use
def cached(ttl_seconds: int | None = None, key_func: Callable | None = None):
    """Decorator for caching function results."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{hashlib.md5(str(args + tuple(kwargs.items())).encode()).hexdigest()}"

            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result

            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl_seconds)
            return result

        return wrapper

    return decorator


def performance_tracked(operation_name: str):
    """Decorator for tracking function performance."""
    return profiler.measure_performance(operation_name)
