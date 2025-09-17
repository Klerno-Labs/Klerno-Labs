"""
Enterprise Performance & Scalability Optimization

Implements enterprise-grade performance optimization with advanced caching,
database optimization, connection pooling, load balancing, and horizontal
scaling capabilities for high-volume operations.
"""
from __future__ import annotations

import asyncio
import asyncpg
import redis
import memcache
import threading
import time
import hashlib  # noqa: F401  # may be used in downstream features
import pickle
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Union, Callable, TypeVar, Generic
from dataclasses import dataclass
from collections import defaultdict, OrderedDict
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
import gc
import psutil
from contextlib import asynccontextmanager
import aiohttp
try:
    import uvloop  # type: ignore
    UVLOOP_AVAILABLE = True
except ImportError:
    uvloop = None
    UVLOOP_AVAILABLE = False
import json

logger = logging.getLogger(__name__)

# Type definitions
T = TypeVar('T')
CacheKey = Union[str, int, tuple]

class CacheStrategy(str):
    """Cache strategies for different use cases."""
    LRU = "lru"
    LFU = "lfu"
    TTL = "ttl"
    WRITE_THROUGH = "write_through"
    WRITE_BACK = "write_back"
    READ_THROUGH = "read_through"

@dataclass
class PerformanceMetrics:
    """Performance metrics tracking."""
    timestamp: datetime
    response_time_ms: float
    memory_usage_mb: float
    cpu_usage_percent: float
    active_connections: int
    cache_hit_ratio: float
    throughput_rps: float
    error_rate: float

@dataclass
class CacheConfig:
    """Cache configuration."""
    strategy: CacheStrategy
    max_size: int
    ttl_seconds: int
    compression: bool = True
    serialization: str = "pickle"  # pickle, json, msgpack

class AdvancedCache(Generic[T]):
    """Advanced multi-level caching system."""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.local_cache: OrderedDict = OrderedDict()
        self.redis_client: Optional[redis.Redis] = None
        self.memcache_client: Optional[memcache.Client] = None
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "memory_usage": 0
        }
        self.lock = threading.RLock()
        self._initialize_backends()
    
    def _initialize_backends(self) -> None:
        """Initialize caching backends."""
        try:
            # Redis for distributed caching
            self.redis_client = redis.Redis(
                host='localhost',
                port=6379,
                db=0,
                decode_responses=False,
                socket_connect_timeout=5,
                socket_timeout=5,
                # retry_on_timeout is deprecated; rely on socket timeouts and health checks
                health_check_interval=30
            )
            self.redis_client.ping()
            logger.info("Redis cache backend initialized")
        except Exception as e:
            logger.warning(f"Redis not available: {e}")
        
        try:
            # Memcached for high-performance caching
            self.memcache_client = memcache.Client(
                ['127.0.0.1:11211'],
                debug=0,
                socket_timeout=5,
                server_max_value_length=1024*1024  # 1MB
            )
            self.memcache_client.set("test", "test", time=1)
            logger.info("Memcached backend initialized")
        except Exception as e:
            logger.warning(f"Memcached not available: {e}")
    
    def _serialize(self, value: Any) -> bytes:
        """Serialize value for storage."""
        if self.config.serialization == "json":
            return json.dumps(value, default=str).encode()
        elif self.config.serialization == "pickle":
            return pickle.dumps(value)
        else:
            return pickle.dumps(value)
    
    def _deserialize(self, data: bytes) -> Any:
        """Deserialize value from storage."""
        if self.config.serialization == "json":
            return json.loads(data.decode())
        elif self.config.serialization == "pickle":
            return pickle.loads(data)
        else:
            return pickle.loads(data)
    
    def _compress(self, data: bytes) -> bytes:
        """Compress data if enabled."""
        if self.config.compression:
            import zlib
            return zlib.compress(data)
        return data
    
    def _decompress(self, data: bytes) -> bytes:
        """Decompress data if needed."""
        if self.config.compression:
            import zlib
            return zlib.decompress(data)
        return data
    
    def _make_key(self, key: CacheKey) -> str:
        """Create standardized cache key."""
        if isinstance(key, (list, tuple)):
            key = ":".join(str(k) for k in key)
        return f"cache:{key}"
    
    def get(self, key: CacheKey) -> Optional[T]:
        """Get value from cache."""
        cache_key = self._make_key(key)
        
        with self.lock:
            # Try local cache first (L1)
            if cache_key in self.local_cache:
                self.stats["hits"] += 1
                # Move to end for LRU
                value = self.local_cache.pop(cache_key)
                self.local_cache[cache_key] = value
                return value["data"]
            
            # Try Redis cache (L2)
            if self.redis_client:
                try:
                    data = self.redis_client.get(cache_key)
                    if data:
                        value = self._deserialize(self._decompress(data))
                        # Promote to local cache
                        self._set_local(cache_key, value)
                        self.stats["hits"] += 1
                        return value
                except Exception as e:
                    logger.warning(f"Redis get error: {e}")
            
            # Try Memcached (L3)
            if self.memcache_client:
                try:
                    data = self.memcache_client.get(cache_key)
                    if data:
                        value = self._deserialize(self._decompress(data))
                        # Promote to higher levels
                        self._set_local(cache_key, value)
                        if self.redis_client:
                            self.redis_client.setex(
                                cache_key,
                                self.config.ttl_seconds,
                                self._compress(self._serialize(value))
                            )
                        self.stats["hits"] += 1
                        return value
                except Exception as e:
                    logger.warning(f"Memcached get error: {e}")
            
            self.stats["misses"] += 1
            return None
    
    def set(self, key: CacheKey, value: T, ttl: Optional[int] = None) -> None:
        """Set value in cache."""
        cache_key = self._make_key(key)
        ttl = ttl or self.config.ttl_seconds
        
        with self.lock:
            # Set in local cache
            self._set_local(cache_key, value, ttl)
            
            # Set in Redis
            if self.redis_client:
                try:
                    serialized = self._serialize(value)
                    compressed = self._compress(serialized)
                    self.redis_client.setex(cache_key, ttl, compressed)
                except Exception as e:
                    logger.warning(f"Redis set error: {e}")
            
            # Set in Memcached
            if self.memcache_client:
                try:
                    serialized = self._serialize(value)
                    compressed = self._compress(serialized)
                    self.memcache_client.set(cache_key, compressed, time=ttl)
                except Exception as e:
                    logger.warning(f"Memcached set error: {e}")
    
    def _set_local(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in local cache."""
        # Evict if at capacity
        if len(self.local_cache) >= self.config.max_size:
            if self.config.strategy == CacheStrategy.LRU:
                # Remove least recently used
                oldest_key = next(iter(self.local_cache))
                del self.local_cache[oldest_key]
                self.stats["evictions"] += 1
        
        expiry = None
        if ttl:
            expiry = datetime.now() + timedelta(seconds=ttl)
        
        self.local_cache[key] = {
            "data": value,
            "expiry": expiry,
            "access_count": 1
        }
    
    def delete(self, key: CacheKey) -> bool:
        """Delete value from cache."""
        cache_key = self._make_key(key)
        deleted = False
        
        with self.lock:
            # Delete from local cache
            if cache_key in self.local_cache:
                del self.local_cache[cache_key]
                deleted = True
            
            # Delete from Redis
            if self.redis_client:
                try:
                    result = self.redis_client.delete(cache_key)
                    if result:
                        deleted = True
                except Exception as e:
                    logger.warning(f"Redis delete error: {e}")
            
            # Delete from Memcached
            if self.memcache_client:
                try:
                    self.memcache_client.delete(cache_key)
                    deleted = True
                except Exception as e:
                    logger.warning(f"Memcached delete error: {e}")
        
        return deleted
    
    def clear(self) -> None:
        """Clear all cache levels."""
        with self.lock:
            self.local_cache.clear()
            
            if self.redis_client:
                try:
                    # Clear only our keys
                    keys = self.redis_client.keys("cache:*")
                    if keys:
                        self.redis_client.delete(*keys)
                except Exception as e:
                    logger.warning(f"Redis clear error: {e}")
            
            if self.memcache_client:
                try:
                    self.memcache_client.flush_all()
                except Exception as e:
                    logger.warning(f"Memcached clear error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_ratio = self.stats["hits"] / total_requests if total_requests > 0 else 0
        
        return {
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "hit_ratio": hit_ratio,
            "evictions": self.stats["evictions"],
            "local_cache_size": len(self.local_cache),
            "memory_usage_mb": self.stats["memory_usage"]
        }

class DatabasePool:
    """Advanced database connection pool."""
    
    def __init__(
        self,
        database_url: str,
        min_connections: int = 5,
        max_connections: int = 20,
        max_queries: int = 50000,
        max_inactive_connection_lifetime: float = 300.0
    ):
        self.database_url = database_url
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.max_queries = max_queries
        self.max_inactive_connection_lifetime = max_inactive_connection_lifetime
        self.pool: Optional[asyncpg.Pool] = None
        self.stats = {
            "total_connections": 0,
            "active_connections": 0,
            "queries_executed": 0,
            "query_errors": 0,
            "avg_query_time": 0.0
        }
        self.query_times = []
        self.lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """Initialize connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=self.min_connections,
                max_size=self.max_connections,
                max_queries=self.max_queries,
                max_inactive_connection_lifetime=self.max_inactive_connection_lifetime,
                command_timeout=30,
                server_settings={
                    'jit': 'off',  # Disable JIT for consistent performance
                    'application_name': 'klerno_enterprise'
                }
            )
            self.stats["total_connections"] = self.max_connections
            logger.info(
                "Database pool initialized with %s-%s connections",
                self.min_connections,
                self.max_connections,
            )
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    @asynccontextmanager
    async def acquire(self):
        """Acquire database connection."""
        if not self.pool:
            await self.initialize()
        
        async with self.pool.acquire() as connection:
            async with self.lock:
                self.stats["active_connections"] += 1
            try:
                yield connection
            finally:
                async with self.lock:
                    self.stats["active_connections"] -= 1
    
    async def execute_query(self, query: str, *args) -> List[Dict]:
        """Execute query with performance tracking."""
        start_time = time.time()
        
        try:
            async with self.acquire() as connection:
                result = await connection.fetch(query, *args)
                
                # Convert records to dicts
                rows = [dict(record) for record in result]
                
                # Track performance
                query_time = (time.time() - start_time) * 1000  # ms
                self.query_times.append(query_time)
                
                # Keep only last 1000 query times
                if len(self.query_times) > 1000:
                    self.query_times = self.query_times[-1000:]
                
                async with self.lock:
                    self.stats["queries_executed"] += 1
                    self.stats["avg_query_time"] = sum(self.query_times) / len(self.query_times)
                
                return rows
                
        except Exception as e:
            async with self.lock:
                self.stats["query_errors"] += 1
            logger.error(f"Query execution error: {e}")
            raise
    
    async def execute_transaction(self, queries: List[tuple]) -> List[Any]:
        """Execute multiple queries in a transaction."""
        start_time = time.time()
        
        try:
            async with self.acquire() as connection:
                async with connection.transaction():
                    results = []
                    for query, args in queries:
                        result = await connection.fetch(query, *args)
                        results.append([dict(record) for record in result])
                    
                    # Track performance
                    query_time = (time.time() - start_time) * 1000  # ms
                    self.query_times.append(query_time)
                    
                    async with self.lock:
                        self.stats["queries_executed"] += len(queries)
                    
                    return results
                    
        except Exception as e:
            async with self.lock:
                self.stats["query_errors"] += 1
            logger.error(f"Transaction execution error: {e}")
            raise
    
    async def close(self) -> None:
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Database pool closed")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        return {
            "total_connections": self.stats["total_connections"],
            "active_connections": self.stats["active_connections"],
            "queries_executed": self.stats["queries_executed"],
            "query_errors": self.stats["query_errors"],
            "avg_query_time_ms": self.stats["avg_query_time"],
            "error_rate": self.stats["query_errors"] / max(self.stats["queries_executed"], 1)
        }

class LoadBalancer:
    """Advanced load balancer with health checking."""
    
    def __init__(self):
        self.backends: List[Dict[str, Any]] = []
        self.current_index = 0
        self.health_checks: Dict[str, bool] = {}
        self.request_counts: Dict[str, int] = defaultdict(int)
        self.response_times: Dict[str, List[float]] = defaultdict(list)
        self.lock = threading.Lock()
        self.health_check_interval = 30  # seconds
        self.health_checker_running = False
    
    def add_backend(
        self, host: str, port: int, weight: int = 1, max_connections: int = 100
    ) -> None:
        """Add backend server."""
        backend = {
            "host": host,
            "port": port,
            "weight": weight,
            "max_connections": max_connections,
            "current_connections": 0,
            "id": f"{host}:{port}"
        }
        
        with self.lock:
            self.backends.append(backend)
            self.health_checks[backend["id"]] = True
            self.request_counts[backend["id"]] = 0
            self.response_times[backend["id"]] = []
        
        logger.info(f"Added backend: {backend['id']}")
        
        # Start health checker if not running
        if not self.health_checker_running:
            self._start_health_checker()
    
    def _start_health_checker(self) -> None:
        """Start background health checker."""
        def health_check_loop():
            self.health_checker_running = True
            while self.health_checker_running:
                asyncio.run(self._check_all_backends())
                time.sleep(self.health_check_interval)
        
        thread = threading.Thread(target=health_check_loop, daemon=True)
        thread.start()
        logger.info("Health checker started")
    
    async def _check_all_backends(self) -> None:
        """Check health of all backends."""
        tasks = []
        for backend in self.backends:
            task = asyncio.create_task(self._check_backend_health(backend))
            tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _check_backend_health(self, backend: Dict[str, Any]) -> None:
        """Check health of a single backend."""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                url = f"http://{backend['host']}:{backend['port']}/health"
                async with session.get(url) as response:
                    is_healthy = response.status == 200
                    
                    with self.lock:
                        self.health_checks[backend["id"]] = is_healthy
                    
                    if not is_healthy:
                        logger.warning(f"Backend {backend['id']} is unhealthy")
        
        except Exception as e:
            with self.lock:
                self.health_checks[backend["id"]] = False
            logger.warning(f"Health check failed for {backend['id']}: {e}")
    
    def get_backend(self, strategy: str = "round_robin") -> Optional[Dict[str, Any]]:
        """Get next backend using specified strategy."""
        with self.lock:
            healthy_backends = [
                backend for backend in self.backends
                if self.health_checks.get(backend["id"], False)
                and backend["current_connections"] < backend["max_connections"]
            ]
            
            if not healthy_backends:
                return None
            
            if strategy == "round_robin":
                backend = healthy_backends[self.current_index % len(healthy_backends)]
                self.current_index += 1
            
            elif strategy == "least_connections":
                backend = min(healthy_backends, key=lambda b: b["current_connections"])
            
            elif strategy == "weighted_round_robin":
                # Simple weighted selection
                total_weight = sum(b["weight"] for b in healthy_backends)
                if total_weight == 0:
                    return None
                
                import random
                weight_sum = 0
                rand = random.randint(1, total_weight)
                
                for backend in healthy_backends:
                    weight_sum += backend["weight"]
                    if rand <= weight_sum:
                        break
            
            elif strategy == "least_response_time":
                # Choose backend with lowest average response time
                def avg_response_time(backend_id):
                    times = self.response_times[backend_id]
                    return sum(times) / len(times) if times else 0
                
                backend = min(healthy_backends, key=lambda b: avg_response_time(b["id"]))
            
            else:
                backend = healthy_backends[0]
            
            # Increment connection count
            backend["current_connections"] += 1
            self.request_counts[backend["id"]] += 1
            
            return backend
    
    def release_backend(self, backend: Dict[str, Any], response_time_ms: float) -> None:
        """Release backend and record performance."""
        with self.lock:
            if backend["current_connections"] > 0:
                backend["current_connections"] -= 1
            
            # Record response time
            response_times = self.response_times[backend["id"]]
            response_times.append(response_time_ms)
            
            # Keep only last 100 response times
            if len(response_times) > 100:
                self.response_times[backend["id"]] = response_times[-100:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get load balancer statistics."""
        with self.lock:
            backend_stats = []
            for backend in self.backends:
                backend_id = backend["id"]
                response_times = self.response_times[backend_id]
                avg_response_time = (
                    sum(response_times) / len(response_times) if response_times else 0
                )
                
                backend_stats.append({
                    "id": backend_id,
                    "healthy": self.health_checks.get(backend_id, False),
                    "current_connections": backend["current_connections"],
                    "max_connections": backend["max_connections"],
                    "request_count": self.request_counts[backend_id],
                    "avg_response_time_ms": avg_response_time
                })
            
            return {
                "total_backends": len(self.backends),
                "healthy_backends": sum(1 for health in self.health_checks.values() if health),
                "backend_stats": backend_stats
            }

def cached(
    ttl: int = 300,
    max_size: int = 1000,
    strategy: CacheStrategy = CacheStrategy.LRU
):
    """Advanced caching decorator."""
    def decorator(func: Callable) -> Callable:
        cache_config = CacheConfig(
            strategy=strategy,
            max_size=max_size,
            ttl_seconds=ttl
        )
        cache = AdvancedCache(cache_config)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            key_parts = [func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(key_parts)
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            cache.set(cache_key, result)
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            key_parts = [func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(key_parts)
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result)
            return result
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

class PerformanceOptimizer:
    """Main performance optimization orchestrator."""
    
    def __init__(self):
        self.cache = AdvancedCache(CacheConfig(
            strategy=CacheStrategy.LRU,
            max_size=10000,
            ttl_seconds=3600
        ))
        self.db_pool = None
        self.load_balancer = LoadBalancer()
        self.metrics_history: List[PerformanceMetrics] = []
        self.thread_pool = ThreadPoolExecutor(max_workers=20)
        self.optimization_rules = []
        
        # Set uvloop for better async performance
        if UVLOOP_AVAILABLE:
            try:
                asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
                logger.info("uvloop enabled for enhanced async performance")
            except Exception as e:
                logger.warning(f"Failed to enable uvloop: {e}")
        else:
            logger.info("uvloop not available, using default event loop")
    
    async def initialize(self, database_url: str) -> None:
        """Initialize performance optimizer."""
        self.db_pool = DatabasePool(database_url)
        await self.db_pool.initialize()
        
        # Add default optimization rules
        self._add_default_optimization_rules()
        
        logger.info("Performance optimizer initialized")
    
    def _add_default_optimization_rules(self) -> None:
        """Add default performance optimization rules."""
        self.optimization_rules = [
            {
                "name": "high_memory_usage",
                "condition": lambda metrics: metrics.memory_usage_mb > 1000,
                "action": self._optimize_memory
            },
            {
                "name": "high_cpu_usage",
                "condition": lambda metrics: metrics.cpu_usage_percent > 80,
                "action": self._optimize_cpu
            },
            {
                "name": "low_cache_hit_ratio",
                "condition": lambda metrics: metrics.cache_hit_ratio < 0.7,
                "action": self._optimize_cache
            },
            {
                "name": "high_response_time",
                "condition": lambda metrics: metrics.response_time_ms > 500,
                "action": self._optimize_response_time
            }
        ]
    
    def collect_metrics(self) -> PerformanceMetrics:
        """Collect current performance metrics."""
        # System metrics
        memory_info = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # Cache metrics
        cache_stats = self.cache.get_stats()
        
        # Database metrics
        db_stats = self.db_pool.get_stats() if self.db_pool else {}
        
    # Load balancer metrics (access directly in metrics below)
        
        metrics = PerformanceMetrics(
            timestamp=datetime.now(timezone.utc),
            response_time_ms=0.0,  # Will be updated by request handlers
            memory_usage_mb=memory_info.used / (1024 * 1024),
            cpu_usage_percent=cpu_percent,
            active_connections=db_stats.get("active_connections", 0),
            cache_hit_ratio=cache_stats.get("hit_ratio", 0.0),
            throughput_rps=0.0,  # Will be calculated
            error_rate=db_stats.get("error_rate", 0.0)
        )
        
        # Store metrics history
        self.metrics_history.append(metrics)
        
        # Keep only last 1000 metrics
        if len(self.metrics_history) > 1000:
            self.metrics_history = self.metrics_history[-1000:]
        
        return metrics
    
    def apply_optimizations(self, metrics: PerformanceMetrics) -> List[str]:
        """Apply optimization rules based on metrics."""
        applied_optimizations = []
        
        for rule in self.optimization_rules:
            try:
                if rule["condition"](metrics):
                    rule["action"](metrics)
                    applied_optimizations.append(rule["name"])
                    logger.info(f"Applied optimization: {rule['name']}")
            except Exception as e:
                logger.error(f"Error applying optimization {rule['name']}: {e}")
        
        return applied_optimizations
    
    def _optimize_memory(self, metrics: PerformanceMetrics) -> None:
        """Optimize memory usage."""
        # Force garbage collection
        gc.collect()
        
        # Clear old cache entries
        if hasattr(self.cache, 'local_cache'):
            current_time = datetime.now()
            expired_keys = []
            for key, value in self.cache.local_cache.items():
                if value.get("expiry") and value["expiry"] < current_time:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.cache.local_cache[key]
        
        logger.info("Memory optimization applied")
    
    def _optimize_cpu(self, metrics: PerformanceMetrics) -> None:
        """Optimize CPU usage."""
        # Reduce thread pool size temporarily
        if self.thread_pool._max_workers > 5:
            self.thread_pool._max_workers = max(5, self.thread_pool._max_workers - 5)
        
        logger.info("CPU optimization applied")
    
    def _optimize_cache(self, metrics: PerformanceMetrics) -> None:
        """Optimize cache performance."""
        # Increase cache size if hit ratio is low
        if self.cache.config.max_size < 20000:
            self.cache.config.max_size = min(20000, self.cache.config.max_size * 2)
        
        # Adjust TTL
        if self.cache.config.ttl_seconds < 7200:
            self.cache.config.ttl_seconds = min(7200, self.cache.config.ttl_seconds * 2)
        
        logger.info("Cache optimization applied")
    
    def _optimize_response_time(self, metrics: PerformanceMetrics) -> None:
        """Optimize response time."""
        # Add more backends if available
        # This would be implemented based on your infrastructure
        
        # Increase connection pool size
        if self.db_pool and self.db_pool.max_connections < 50:
            self.db_pool.max_connections = min(50, self.db_pool.max_connections + 5)
        
        logger.info("Response time optimization applied")
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        if not self.metrics_history:
            return {"error": "No metrics available"}
        
        recent_metrics = self.metrics_history[-100:]  # Last 100 measurements
        
        # Calculate averages
        avg_response_time = sum(m.response_time_ms for m in recent_metrics) / len(recent_metrics)
        avg_memory_usage = sum(m.memory_usage_mb for m in recent_metrics) / len(recent_metrics)
        avg_cpu_usage = sum(m.cpu_usage_percent for m in recent_metrics) / len(recent_metrics)
        avg_cache_hit_ratio = sum(m.cache_hit_ratio for m in recent_metrics) / len(recent_metrics)
        
        # Performance score (0-100)
        score_factors = []
        
        # Response time score (lower is better)
        response_score = max(0, 100 - (avg_response_time / 10))  # 1000ms = 0 score
        score_factors.append(response_score)
        
        # Memory usage score (lower is better)
        memory_score = max(0, 100 - (avg_memory_usage / 20))  # 2GB = 0 score
        score_factors.append(memory_score)
        
        # CPU usage score (lower is better)
        cpu_score = max(0, 100 - avg_cpu_usage)
        score_factors.append(cpu_score)
        
        # Cache hit ratio score
        cache_score = avg_cache_hit_ratio * 100
        score_factors.append(cache_score)
        
        performance_score = sum(score_factors) / len(score_factors)
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "performance_score": round(performance_score, 2),
            "averages": {
                "response_time_ms": round(avg_response_time, 2),
                "memory_usage_mb": round(avg_memory_usage, 2),
                "cpu_usage_percent": round(avg_cpu_usage, 2),
                "cache_hit_ratio": round(avg_cache_hit_ratio, 3)
            },
            "cache_stats": self.cache.get_stats(),
            "database_stats": self.db_pool.get_stats() if self.db_pool else {},
            "load_balancer_stats": self.load_balancer.get_stats(),
            "recommendations": self._get_recommendations(
                recent_metrics[-1] if recent_metrics else None
            )
        }
    
    async def initialize_cache_layers(self) -> None:
        """Initialize multiple cache layers for optimal performance."""
        try:
            # Initialize memory cache (already done in __init__)
            logger.info("Memory cache layer initialized")
            
            # Initialize Redis cache if available
            try:
                import redis.asyncio as redis
                self.redis_cache = redis.Redis(
                    host=os.getenv('REDIS_HOST', 'localhost'),
                    port=int(os.getenv('REDIS_PORT', 6379)),
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                await self.redis_cache.ping()
                logger.info("Redis cache layer initialized")
            except Exception as e:
                logger.warning(f"Redis cache not available: {e}")
                self.redis_cache = None
            
            # Initialize memcached if available
            try:
                import pymemcache.client
                self.memcached_client = pymemcache.client.MemcachedClient(
                    (os.getenv('MEMCACHED_HOST', 'localhost'), 
                     int(os.getenv('MEMCACHED_PORT', 11211))),
                    timeout=5
                )
                logger.info("Memcached cache layer initialized")
            except ImportError:
                logger.warning("pymemcache not installed, skipping memcached layer")
                self.memcached_client = None
            except Exception as e:
                logger.warning(f"Memcached not available: {e}")
                self.memcached_client = None
            
            # Initialize distributed cache statistics
            self.cache_layers_stats = {
                "memory": {"hits": 0, "misses": 0, "errors": 0},
                "redis": {"hits": 0, "misses": 0, "errors": 0},
                "memcached": {"hits": 0, "misses": 0, "errors": 0}
            }
            
        except Exception as e:
            logger.error(f"Error initializing cache layers: {e}")
    
    async def run_performance_benchmarks(self) -> Dict[str, Any]:
        """Run comprehensive performance benchmarks."""
        benchmark_results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cache_performance": {},
            "database_performance": {},
            "cpu_performance": {},
            "memory_performance": {},
            "network_performance": {}
        }
        
        try:
            # Cache benchmark
            cache_start = time.time()
            for i in range(1000):
                key = f"benchmark_key_{i}"
                value = f"benchmark_value_{i}" * 10
                self.cache.set(key, value)
                retrieved = self.cache.get(key)
                if retrieved != value:
                    logger.warning(f"Cache benchmark failed for key {key}")
            
            cache_duration = time.time() - cache_start
            benchmark_results["cache_performance"] = {
                "operations": 2000,
                "duration_seconds": round(cache_duration, 3),
                "ops_per_second": round(2000 / cache_duration, 2)
            }
            
            # Database benchmark (if available)
            if self.db_pool:
                db_start = time.time()
                for i in range(100):
                    await self.db_pool.execute_query("SELECT 1 as test_value")
                
                db_duration = time.time() - db_start
                benchmark_results["database_performance"] = {
                    "queries": 100,
                    "duration_seconds": round(db_duration, 3),
                    "queries_per_second": round(100 / db_duration, 2)
                }
            
            # CPU benchmark
            cpu_start = time.time()
            result = sum(i * i for i in range(100000))
            cpu_duration = time.time() - cpu_start
            benchmark_results["cpu_performance"] = {
                "operations": 100000,
                "duration_seconds": round(cpu_duration, 3),
                "result": result
            }
            
            # Memory benchmark
            memory_start = time.time()
            test_data = []
            for i in range(10000):
                test_data.append({"id": i, "data": f"test_data_{i}" * 10})
            
            memory_duration = time.time() - memory_start
            del test_data  # Clean up
            benchmark_results["memory_performance"] = {
                "allocations": 10000,
                "duration_seconds": round(memory_duration, 3)
            }
            
            # Overall score calculation
            cache_score = min(
                100,
                1000 / benchmark_results["cache_performance"]["duration_seconds"],
            )
            cpu_score = min(100, 1.0 / benchmark_results["cpu_performance"]["duration_seconds"])
            memory_score = min(
                100,
                1.0 / benchmark_results["memory_performance"]["duration_seconds"],
            )
            
            benchmark_results["overall_score"] = round(
                (cache_score + cpu_score + memory_score) / 3,
                2,
            )
            
            logger.info(
                "Performance benchmarks completed with overall score: %s",
                benchmark_results["overall_score"],
            )
            
        except Exception as e:
            logger.error(f"Error running performance benchmarks: {e}")
            benchmark_results["error"] = str(e)
        
        return benchmark_results
    
    def get_performance_baseline(self) -> Dict[str, Any]:
        """Get performance baseline metrics for comparison."""
        if not self.metrics_history:
            return {
                "error": "No metrics history available",
                "recommendation": "Run the system for a while to establish baseline"
            }
        
        # Calculate baseline from first 10% of metrics or minimum 10 samples
        baseline_count = max(10, len(self.metrics_history) // 10)
        baseline_metrics = self.metrics_history[:baseline_count]
        
        if not baseline_metrics:
            return {"error": "Insufficient metrics for baseline"}
        
        baseline = {
            "sample_count": len(baseline_metrics),
            "time_range": {
                "start": baseline_metrics[0].timestamp.isoformat(),
                "end": baseline_metrics[-1].timestamp.isoformat()
            },
            "metrics": {
                "avg_response_time_ms": round(
                    sum(m.response_time_ms for m in baseline_metrics) / len(baseline_metrics), 2
                ),
                "avg_memory_usage_mb": round(
                    sum(m.memory_usage_mb for m in baseline_metrics) / len(baseline_metrics), 2
                ),
                "avg_cpu_usage_percent": round(
                    sum(m.cpu_usage_percent for m in baseline_metrics) / len(baseline_metrics), 2
                ),
                "avg_cache_hit_ratio": round(
                    sum(m.cache_hit_ratio for m in baseline_metrics) / len(baseline_metrics), 3
                )
            }
        }
        
        # Compare with recent metrics if available
        if len(self.metrics_history) > baseline_count:
            recent_metrics = self.metrics_history[-10:]  # Last 10 metrics
            current = {
                "avg_response_time_ms": round(
                    sum(m.response_time_ms for m in recent_metrics) / len(recent_metrics), 2
                ),
                "avg_memory_usage_mb": round(
                    sum(m.memory_usage_mb for m in recent_metrics) / len(recent_metrics), 2
                ),
                "avg_cpu_usage_percent": round(
                    sum(m.cpu_usage_percent for m in recent_metrics) / len(recent_metrics), 2
                ),
                "avg_cache_hit_ratio": round(
                    sum(m.cache_hit_ratio for m in recent_metrics) / len(recent_metrics), 3
                )
            }
            
            baseline["current_comparison"] = {
                "response_time_change_percent": round(
                    (
                        (
                            current["avg_response_time_ms"]
                            - baseline["metrics"]["avg_response_time_ms"]
                        )
                        / baseline["metrics"]["avg_response_time_ms"]
                    )
                    * 100,
                    2,
                ),
                "memory_change_percent": round(
                    ((current["avg_memory_usage_mb"] - baseline["metrics"]["avg_memory_usage_mb"]) 
                     / baseline["metrics"]["avg_memory_usage_mb"]) * 100, 2
                ),
                "cpu_change_percent": round(
                    (
                        (
                            current["avg_cpu_usage_percent"]
                            - baseline["metrics"]["avg_cpu_usage_percent"]
                        )
                        / baseline["metrics"]["avg_cpu_usage_percent"]
                    )
                    * 100,
                    2,
                ),
                "cache_hit_ratio_change_percent": round(
                    ((current["avg_cache_hit_ratio"] - baseline["metrics"]["avg_cache_hit_ratio"]) 
                     / baseline["metrics"]["avg_cache_hit_ratio"]) * 100, 2
                )
            }
        
        return baseline
    
    def _get_recommendations(self, latest_metrics: Optional[PerformanceMetrics]) -> List[str]:
        """Get performance improvement recommendations."""
        if not latest_metrics:
            return []
        
        recommendations = []
        
        if latest_metrics.response_time_ms > 200:
            recommendations.append("Consider enabling more aggressive caching")
            recommendations.append("Optimize database queries with indexing")
            recommendations.append("Consider adding more backend servers")
        
        if latest_metrics.memory_usage_mb > 500:
            recommendations.append("Review memory usage patterns")
            recommendations.append("Consider reducing cache size")
            recommendations.append("Implement memory pooling")
        
        if latest_metrics.cpu_usage_percent > 70:
            recommendations.append("Optimize CPU-intensive operations")
            recommendations.append("Consider horizontal scaling")
            recommendations.append("Review algorithm efficiency")
        
        if latest_metrics.cache_hit_ratio < 0.8:
            recommendations.append("Increase cache TTL for stable data")
            recommendations.append("Implement cache warming strategies")
            recommendations.append("Review cache key strategies")
        
        return recommendations

# Global performance optimizer instance
performance_optimizer = PerformanceOptimizer()

async def initialize_performance_system(database_url: str) -> None:
    """Initialize the performance optimization system."""
    await performance_optimizer.initialize(database_url)

def get_performance_dashboard() -> Dict[str, Any]:
    """Get performance dashboard data."""
    return performance_optimizer.get_performance_report()

# Convenience functions
async def optimized_query(query: str, *args) -> List[Dict]:
    """Execute optimized database query."""
    if performance_optimizer.db_pool:
        return await performance_optimizer.db_pool.execute_query(query, *args)
    else:
        raise RuntimeError("Database pool not initialized")

def get_cached_data(key: str) -> Any:
    """Get data from cache."""
    return performance_optimizer.cache.get(key)

def set_cached_data(key: str, value: Any, ttl: int = 300) -> None:
    """Set data in cache."""
    performance_optimizer.cache.set(key, value, ttl)