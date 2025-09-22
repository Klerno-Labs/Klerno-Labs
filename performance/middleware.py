"""
Performance Middleware for FastAPI
Advanced middleware for performance monitoring and optimization
"""

import asyncio
import time
from collections.abc import Callable

from app.monitoring.logging import get_logger
from app.monitoring.metrics import metrics
from app.performance.caching import cache
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = get_logger("performance")


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Middleware for performance monitoring and optimization"""

    def __init__(self, app, cache_enabled: bool = True, metrics_enabled: bool = True):
        super().__init__(app)
        self.cache_enabled = cache_enabled
        self.metrics_enabled = metrics_enabled
        self.slow_request_threshold = 2.0  # seconds

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with performance monitoring"""
        start_time = time.time()
        request_id = id(request)

        # Get request info
        method = request.method
        path = request.url.path
        user_agent = request.headers.get("user-agent", "")

        # Log request start
        logger.debug(
            f"Request started: {method} {path}",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "user_agent": user_agent,
            },
        )

        try:
            # Check cache for GET requests
            if self.cache_enabled and method == "GET" and self._is_cacheable(path):
                cached_response = await self._get_cached_response(request)
                if cached_response:
                    response_time = time.time() - start_time

                    # Track cache hit metrics
                    if self.metrics_enabled:
                        metrics.increment(
                            "http_cache_hits", tags={"endpoint": path, "method": method}
                        )
                        metrics.histogram(
                            "http_response_time",
                            response_time * 1000,
                            tags={"endpoint": path, "method": method, "cache": "hit"},
                        )

                    logger.info(
                        f"Cache hit: {method} {path} - {response_time:.3f}s",
                        extra={
                            "request_id": request_id,
                            "response_time": response_time,
                            "cache_hit": True,
                        },
                    )

                    return cached_response

            # Process request
            response = await call_next(request)
            response_time = time.time() - start_time

            # Cache successful GET responses
            if (
                self.cache_enabled
                and method == "GET"
                and response.status_code == 200
                and self._is_cacheable(path)
            ):
                await self._cache_response(request, response)

            # Track metrics
            if self.metrics_enabled:
                metrics.increment(
                    "http_requests_total",
                    tags={
                        "endpoint": path,
                        "method": method,
                        "status_code": str(response.status_code),
                    },
                )

                metrics.histogram(
                    "http_response_time",
                    response_time * 1000,
                    tags={
                        "endpoint": path,
                        "method": method,
                        "status_code": str(response.status_code),
                        "cache": "miss",
                    },
                )

                if response.status_code >= 400:
                    metrics.increment(
                        "http_errors_total",
                        tags={
                            "endpoint": path,
                            "method": method,
                            "status_code": str(response.status_code),
                        },
                    )

            # Log slow requests
            if response_time > self.slow_request_threshold:
                logger.warning(
                    f"Slow request: {method} {path} - {response_time:.3f}s",
                    extra={
                        "request_id": request_id,
                        "response_time": response_time,
                        "status_code": response.status_code,
                        "slow_request": True,
                    },
                )
            else:
                logger.info(
                    f"Request completed: {method} {path} - {response_time:.3f}s",
                    extra={
                        "request_id": request_id,
                        "response_time": response_time,
                        "status_code": response.status_code,
                    },
                )

            # Add performance headers
            response.headers["X-Response-Time"] = f"{response_time:.3f}s"
            response.headers["X-Request-ID"] = str(request_id)

            return response

        except Exception as e:
            response_time = time.time() - start_time

            # Track error metrics
            if self.metrics_enabled:
                metrics.increment(
                    "http_errors_total",
                    tags={"endpoint": path, "method": method, "status_code": "500"},
                )

            logger.error(
                f"Request failed: {method} {path} - {response_time:.3f}s - {str(e)}",
                extra={
                    "request_id": request_id,
                    "response_time": response_time,
                    "error": str(e),
                },
            )

            raise

    def _is_cacheable(self, path: str) -> bool:
        """Check if path is cacheable"""
        cacheable_paths = ["/dashboard", "/analytics", "/health", "/static"]

        # Don't cache API endpoints that might have user-specific data
        non_cacheable_paths = ["/auth", "/admin", "/api/user"]

        # Check if path starts with cacheable prefix
        for cacheable in cacheable_paths:
            if path.startswith(cacheable):
                return True

        # Check if path starts with non-cacheable prefix
        for non_cacheable in non_cacheable_paths:
            if path.startswith(non_cacheable):
                return False

        return False

    async def _get_cached_response(self, request: Request) -> Response:
        """Get cached response if available"""
        cache_key = self._get_cache_key(request)
        cached_data = await cache.get(cache_key)

        if cached_data:
            return Response(
                content=cached_data["content"],
                status_code=cached_data["status_code"],
                headers=cached_data["headers"],
                media_type=cached_data["media_type"],
            )

        return None

    async def _cache_response(self, request: Request, response: Response):
        """Cache response data"""
        try:
            # Read response content
            content = b""
            async for chunk in response.body_iterator:
                content += chunk

            # Prepare cache data
            cache_data = {
                "content": content,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "media_type": response.media_type,
            }

            # Cache with appropriate TTL
            cache_key = self._get_cache_key(request)
            ttl = self._get_cache_ttl(request.url.path)

            await cache.set(cache_key, cache_data, ttl)

            # Recreate response with content
            response.body_iterator = iter([content])

        except Exception as e:
            logger.error(f"Cache write error: {e}")

    def _get_cache_key(self, request: Request) -> str:
        """Generate cache key for request"""
        return f"response:{request.method}:{request.url.path}:{request.url.query}"

    def _get_cache_ttl(self, path: str) -> int:
        """Get cache TTL based on path"""
        ttl_map = {
            "/dashboard": 300,  # 5 minutes
            "/analytics": 600,  # 10 minutes
            "/health": 60,  # 1 minute
            "/static": 3600,  # 1 hour
        }

        for prefix, ttl in ttl_map.items():
            if path.startswith(prefix):
                return ttl

        return 300  # Default 5 minutes


class AsyncOptimizationMiddleware(BaseHTTPMiddleware):
    """Middleware for async optimization"""

    def __init__(self, app, max_request_concurrency: int = 100):
        super().__init__(app)
        self.semaphore = asyncio.Semaphore(max_request_concurrency)
        self.active_requests = 0

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with concurrency control"""
        async with self.semaphore:
            self.active_requests += 1

            try:
                # Add concurrency info to request
                request.state.active_requests = self.active_requests

                response = await call_next(request)

                # Add concurrency headers
                response.headers["X-Active-Requests"] = str(self.active_requests)

                return response

            finally:
                self.active_requests -= 1
