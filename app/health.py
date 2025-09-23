"""
Klerno Labs - Enhanced Health Checks and Monitoring
==================================================
Comprehensive health checks and metrics for horizontal scaling
"""

import asyncio
import time
from datetime import datetime
from typing import Any, Mapping, cast

import psutil

try:
    import psycopg2  # type: ignore
except Exception:  # pragma: no cover - optional dependency in some environments
    psycopg2 = None  # type: ignore

try:
    import redis as redis_lib  # type: ignore
except Exception:  # pragma: no cover - optional dependency in some environments
    redis_lib = None  # type: ignore
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel


class HealthStatus(BaseModel):
    """Health check response model"""

    status: str
    timestamp: str
    version: str
    environment: str
    instance_id: str | None = None
    checks: dict[str, Any]
    uptime_seconds: float
    system: dict[str, Any]


class MetricsResponse(BaseModel):
    """Metrics response model"""

    timestamp: str
    instance_id: str | None = None
    system: dict[str, Any]
    application: dict[str, Any]
    database: dict[str, Any]
    cache: dict[str, Any]


class HealthChecker:
    """Comprehensive health checking for all services"""

    def __init__(self, app: FastAPI):
        self.app = app
        self.start_time = time.time()
        self.version = "1.0.0"  # Should be loaded from environment
        self.environment = "production"  # Should be loaded from environment
        self.instance_id = None  # Should be loaded from environment

    async def check_database(self) -> dict[str, Any]:
        """Check PostgreSQL database connectivity and performance"""
        try:
            # Use connection from settings
            from app.settings import get_settings

            settings = get_settings()

            # Parse DATABASE_URL if available
            db_url = getattr(settings, "database_url", None)
            if not db_url:
                return {
                    "status": "unknown",
                    "message": "Database URL not configured",
                    "response_time_ms": 0,
                }

            start_time = time.time()

            # Simple connection test
            if psycopg2 is None:
                return {
                    "status": "unknown",
                    "message": "psycopg2 not available in this environment",
                    "response_time_ms": 0,
                }

            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            conn.close()

            response_time = (time.time() - start_time) * 1000

            return {
                "status": "healthy",
                "message": "Database connection successful",
                "response_time_ms": round(response_time, 2),
                "result": result[0] if result else None,
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Database connection failed: {str(e)}",
                "response_time_ms": 0,
            }

    async def check_cache(self) -> dict[str, Any]:
        """Check Redis cache connectivity and performance"""
        try:
            start_time = time.time()

            # Use Redis URL from settings
            if redis_lib is None:
                return {
                    "status": "unknown",
                    "message": "redis library not available",
                    "response_time_ms": 0,
                }

            # Correct Redis URL (no spaces) and use the imported redis_lib
            redis_client = redis_lib.Redis.from_url(
                "redis://redis:6379/0", decode_responses=True
            )

            # Test basic operations
            test_key = "health_check_test"
            redis_client.set(test_key, "test_value", ex=60)
            redis_client.get(test_key)
            redis_client.delete(test_key)

            response_time = (time.time() - start_time) * 1000

            # Get cache info and normalize result to a mapping
            info = redis_client.info()
            # redis client implementations can return awaitable results in some environments
            info_obj = await info if asyncio.iscoroutine(info) else info  # type: ignore[var-annotated]
            # Cast to a mapping for the type checker; runtime will still work with dict-like objects
            info_obj = cast(Mapping[str, Any], info_obj)

            # Now use info_obj as a mapping safely
            return {
                "status": "healthy",
                "message": "Cache connection successful",
                "response_time_ms": round(response_time, 2),
                "memory_usage_mb": round(
                    info_obj.get("used_memory", 0) / 1024 / 1024, 2
                ),
                "connected_clients": info_obj.get("connected_clients", 0),
                "total_commands_processed": info_obj.get("total_commands_processed", 0),
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Cache connection failed: {str(e)}",
                "response_time_ms": 0,
            }

    async def check_external_apis(self) -> dict[str, Any]:
        """Check external API dependencies"""
        checks = {}

        # XRPL Network check
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                start_time = time.time()
                from aiohttp import ClientTimeout

                timeout = ClientTimeout(total=5)
                async with session.get(
                    "https://s2.ripple.com:51234", timeout=timeout
                ) as response:
                    response_time = (time.time() - start_time) * 1000
                    checks["xrpl"] = {
                        "status": "healthy" if response.status == 200 else "degraded",
                        "response_time_ms": round(response_time, 2),
                        "status_code": response.status,
                    }
        except Exception as e:
            checks["xrpl"] = {
                "status": "unhealthy",
                "message": f"XRPL connection failed: {str(e)}",
                "response_time_ms": 0,
            }

        return checks

    def get_system_metrics(self) -> dict[str, Any]:
        """Get system resource metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()

            # Memory metrics
            memory = psutil.virtual_memory()

            # Disk metrics
            disk = psutil.disk_usage("/")

            # Network metrics
            network = psutil.net_io_counters()

            return {
                "cpu": {"percent": cpu_percent, "count": cpu_count},
                "memory": {
                    "total_mb": round(memory.total / 1024 / 1024, 2),
                    "available_mb": round(memory.available / 1024 / 1024, 2),
                    "used_mb": round(memory.used / 1024 / 1024, 2),
                    "percent": memory.percent,
                },
                "disk": {
                    "total_gb": round(disk.total / 1024 / 1024 / 1024, 2),
                    "free_gb": round(disk.free / 1024 / 1024 / 1024, 2),
                    "used_gb": round(disk.used / 1024 / 1024 / 1024, 2),
                    "percent": (
                        round((disk.used / disk.total) * 100, 2)
                        if getattr(disk, "total", 0)
                        else 0
                    ),
                },
                "network": {
                    "bytes_sent": getattr(network, "bytes_sent", 0),
                    "bytes_recv": getattr(network, "bytes_recv", 0),
                    "packets_sent": getattr(network, "packets_sent", 0),
                    "packets_recv": getattr(network, "packets_recv", 0),
                },
            }
        except Exception as e:
            return {"error": f"Failed to get system metrics: {str(e)}"}

    async def comprehensive_health_check(self) -> HealthStatus:
        """Perform comprehensive health check"""
        start_time = time.time()

        # Run all checks concurrently and assign explicitly to avoid
        # ambiguous multiple-assignment types that confuse static analysis.
        results = await asyncio.gather(
            self.check_database(),
            self.check_cache(),
            self.check_external_apis(),
            return_exceptions=True,
        )

        # Each result may be a dict or an Exception when return_exceptions=True
        database_check: dict[str, Any] | BaseException = results[0]
        cache_check: dict[str, Any] | BaseException = results[1]
        external_checks: dict[str, Any] | BaseException = results[2]

        # Determine overall status
        checks = {
            "database": (
                database_check
                if not isinstance(database_check, Exception)
                else {"status": "error", "message": str(database_check)}
            ),
            "cache": (
                cache_check
                if not isinstance(cache_check, Exception)
                else {"status": "error", "message": str(cache_check)}
            ),
            "external": (
                external_checks
                if not isinstance(external_checks, Exception)
                else {"status": "error", "message": str(external_checks)}
            ),
            "response_time_ms": round((time.time() - start_time) * 1000, 2),
        }

        # Determine overall health status
        all_healthy = all(
            check.get("status") == "healthy"
            for check in [database_check, cache_check]
            if isinstance(check, dict)
        )

        overall_status = "healthy" if all_healthy else "unhealthy"

        return HealthStatus(
            status=overall_status,
            timestamp=datetime.utcnow().isoformat() + "Z",
            version=self.version,
            environment=self.environment,
            instance_id=self.instance_id,
            checks=checks,
            uptime_seconds=round(time.time() - self.start_time, 2),
            system=self.get_system_metrics(),
        )

    async def get_metrics(self) -> MetricsResponse:
        """Get comprehensive metrics for monitoring"""
        try:
            # Get system metrics
            system_metrics = self.get_system_metrics()

            # Get application metrics
            app_metrics = {
                "uptime_seconds": round(time.time() - self.start_time, 2),
                "version": self.version,
                "environment": self.environment,
                "process_id": psutil.Process().pid,
                "threads": psutil.Process().num_threads(),
                "memory_info": {
                    "rss_mb": round(
                        psutil.Process().memory_info().rss / 1024 / 1024, 2
                    ),
                    "vms_mb": round(
                        psutil.Process().memory_info().vms / 1024 / 1024, 2
                    ),
                },
                "cpu_percent": psutil.Process().cpu_percent(),
            }

            # Get database metrics
            db_metrics = await self.check_database()

            # Get cache metrics
            cache_metrics = await self.check_cache()

            return MetricsResponse(
                timestamp=datetime.utcnow().isoformat() + "Z",
                instance_id=self.instance_id,
                system=system_metrics,
                application=app_metrics,
                database=db_metrics,
                cache=cache_metrics,
            )

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get metrics: {str(e)}",
            )


# Global instance
health_checker = None


def init_health_checker(app: FastAPI) -> HealthChecker:
    """Initialize health checker"""
    # Assign the module-level health_checker so callers can retrieve it
    # using get_health_checker(). We intentionally bind here.
    global health_checker
    health_checker = HealthChecker(app)
    return health_checker


def get_health_checker() -> HealthChecker:
    """Get health checker instance"""
    # No global statement required for read access; just ensure it's initialized.
    if health_checker is None:
        raise RuntimeError("Health checker not initialized")
    return health_checker
