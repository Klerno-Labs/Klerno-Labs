"""Performance monitoring and optimization utilities for Klerno Labs.
Provides response time tracking, caching, and real - time performance metrics.
"""

import asyncio
import time
import weakref
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, cast

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


@dataclass
class PerformanceMetrics:
    """Real - time performance metrics tracking."""

    endpoint: str
    method: str
    response_time_ms: float
    status_code: int
    timestamp: datetime
    user_agent: str | None = None
    remote_addr: str | None = None


class PerformanceMonitor:
    """Tracks API performance metrics with sub - 100ms targeting."""

    def __init__(self, max_metrics: int = 1000):
        self.metrics: deque = deque(maxlen=max_metrics)
        self.endpoint_stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "count": 0,
                "total_time": 0.0,
                "avg_time": 0.0,
                "min_time": float("inf"),
                "max_time": 0.0,
                "p95_time": 0.0,
                "recent_times": deque(maxlen=100),
            },
        )

    def record_metric(self, metric: PerformanceMetrics) -> None:
        """Record a performance metric."""
        self.metrics.append(metric)

        # Update endpoint statistics
        key = f"{metric.method} {metric.endpoint}"
        stats = self.endpoint_stats[key]

        stats["count"] += 1
        stats["total_time"] += metric.response_time_ms
        stats["avg_time"] = stats["total_time"] / stats["count"]
        stats["min_time"] = min(stats["min_time"], metric.response_time_ms)
        stats["max_time"] = max(stats["max_time"], metric.response_time_ms)
        stats["recent_times"].append(metric.response_time_ms)

        # Calculate P95
        if len(stats["recent_times"]) >= 5:
            sorted_times = sorted(stats["recent_times"])
            p95_index = int(len(sorted_times) * 0.95)
            stats["p95_time"] = sorted_times[p95_index]

    def get_slow_endpoints(
        self,
        threshold_ms: float = 100.0,
    ) -> dict[str, dict[str, Any]]:
        """Get endpoints exceeding the response time threshold."""
        return {
            endpoint: stats
            for endpoint, stats in self.endpoint_stats.items()
            if stats["avg_time"] > threshold_ms
        }

    def get_summary(self) -> dict[str, Any]:
        """Get performance summary."""
        recent_metrics = list(self.metrics)[-100:] if len(self.metrics) > 0 else []

        if not recent_metrics:
            return {"total_requests": 0, "avg_response_time": 0}

        total_time = sum(m.response_time_ms for m in recent_metrics)
        avg_time = total_time / len(recent_metrics)

        return {
            "total_requests": len(self.metrics),
            "recent_requests": len(recent_metrics),
            "avg_response_time_ms": round(avg_time, 2),
            "slow_endpoints_count": len(self.get_slow_endpoints()),
            "target_met": avg_time < 100.0,
        }


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Middleware to track API response times with sub - 100ms targeting."""

    def __init__(self, app: Any, monitor: PerformanceMonitor) -> None:
        super().__init__(app)
        self.monitor = monitor

    async def dispatch(self, request: Request, call_next: Callable[..., Any]) -> Any:
        start_time = time.perf_counter()

        response = await call_next(request)

        end_time = time.perf_counter()
        response_time_ms = (end_time - start_time) * 1000

        # Record metric
        metric = PerformanceMetrics(
            endpoint=str(request.url.path),
            method=request.method,
            response_time_ms=response_time_ms,
            status_code=response.status_code,
            timestamp=datetime.utcnow(),
            user_agent=request.headers.get("user - agent"),
            remote_addr=request.client.host if request.client else None,
        )

        self.monitor.record_metric(metric)

        # Add performance headers
        metric.user_agent = request.headers.get("user-agent")
        response.headers["X-Response-Time-Ms"] = str(round(response_time_ms, 2))
        if response_time_ms > 100:
            response.headers["X-Performance-Warning"] = "slow-response"

        return response


class InMemoryCache:
    """Simple in - memory cache with TTL support for high - performance data access."""

    def __init__(self, default_ttl: int = 300) -> None:  # 5 minutes default
        self.cache: dict[str, dict[str, Any]] = {}
        self.default_ttl = default_ttl

    def get(self, key: str) -> Any | None:
        """Get cached value if not expired."""
        if key not in self.cache:
            return None

        item = self.cache[key]
        if datetime.utcnow() > item["expires"]:
            del self.cache[key]
            return None

        return item["value"]

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set cached value with TTL."""
        ttl = ttl or self.default_ttl
        expires = datetime.utcnow() + timedelta(seconds=ttl)

        self.cache[key] = {
            "value": value,
            "expires": expires,
            "created": datetime.utcnow(),
        }

    def delete(self, key: str) -> bool:
        """Delete cached value."""
        return self.cache.pop(key, None) is not None

    def clear(self) -> None:
        """Clear all cached values."""
        self.cache.clear()

    def cleanup_expired(self) -> int:
        """Remove expired entries and return count of removed items."""
        now = datetime.utcnow()
        expired_keys = [
            key for key, item in self.cache.items() if now > item["expires"]
        ]

        for key in expired_keys:
            del self.cache[key]

        return len(expired_keys)

    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {
            "total_items": len(self.cache),
            "memory_usage_estimate": sum(
                len(str(item["value"])) for item in self.cache.values()
            ),
            "expired_items_cleaned": self.cleanup_expired(),
        }


def performance_cache(
    ttl: int = 60,
    key_func: Callable | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for caching function results with TTL."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        cache = InMemoryCache(default_ttl=ttl)

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = (
                    f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
                )

            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = await func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = (
                    f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
                )

            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result

        # Return appropriate wrapper based on whether function is async
        if asyncio.iscoroutinefunction(func):
            cast("Any", async_wrapper).cache = cache
            return async_wrapper
        cast("Any", sync_wrapper).cache = cache
        return sync_wrapper

    return decorator


# Global instances
performance_monitor = PerformanceMonitor()
app_cache = InMemoryCache()


# Optimized WebSocket connection management


class OptimizedLiveHub:
    """Enhanced LiveHub with performance optimizations."""

    def __init__(self) -> None:
        self._clients: dict[Any, set[str]] = {}
        self._lock = asyncio.Lock()
        self._connection_pool: weakref.WeakSet = weakref.WeakSet()
        self._message_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._stats = {
            "messages_sent": 0,
            "connections_active": 0,
            "messages_queued": 0,
            "reconnections": 0,
        }
        self._processor_task: asyncio.Task[Any] | None = None

    async def _start_processor(self) -> None:
        """Start the background message processor if not already running."""
        if self._processor_task is None or self._processor_task.done():
            self._processor_task = asyncio.create_task(self._process_messages())

    async def add(self, ws: Any) -> None:
        """Add WebSocket with immediate acceptance."""
        await ws.accept()
        async with self._lock:
            self._clients[ws] = set()
            self._connection_pool.add(ws)
            self._stats["connections_active"] = len(self._clients)

        # Start processor if needed
        await self._start_processor()

    async def remove(self, ws: Any) -> None:
        """Remove WebSocket connection."""
        async with self._lock:
            self._clients.pop(ws, None)
            self._stats["connections_active"] = len(self._clients)

    async def update_watch(self, ws: Any, watch: set[str]) -> None:
        """Update watch list for WebSocket."""
        async with self._lock:
            if ws in self._clients:
                self._clients[ws] = {w.strip().lower() for w in watch if w}

    async def publish(self, item: dict[str, Any]) -> None:
        """Publish message to relevant clients with queuing."""
        fa = (item.get("from_addr") or "").lower()
        ta = (item.get("to_addr") or "").lower()

        message = {"type": "tx", "item": item}

        async with self._lock:
            targets = []
            for ws, watch in self._clients.items():
                if not watch or fa in watch or ta in watch:
                    targets.append(ws)

        # Queue messages for batch processing
        for ws in targets:
            try:
                await self._message_queue.put((ws, message))
                self._stats["messages_queued"] += 1
            except asyncio.QueueFull:
                # Skip if queue is full to prevent blocking
                pass

    async def _process_messages(self) -> None:
        """Background task to process message queue."""
        while True:
            try:
                ws, message = await self._message_queue.get()
                try:
                    await ws.send_json(message)
                    self._stats["messages_sent"] += 1
                except Exception:
                    # Remove dead connections
                    await self.remove(ws)
                finally:
                    self._message_queue.task_done()
            except Exception:
                await asyncio.sleep(0.1)

    def get_stats(self) -> dict[str, Any]:
        """Get hub performance statistics."""
        return {
            **self._stats,
            "queue_size": self._message_queue.qsize(),
            "max_queue_size": self._message_queue.maxsize,
        }
