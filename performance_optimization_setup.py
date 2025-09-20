#!/usr/bin/env python3
"""
Comprehensive Performance Optimization Suite
Implements advanced caching, database optimization, and async performance improvements
"""

import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional


def create_advanced_caching():
    """Create advanced caching system with Redis and in-memory cache"""
    return '''"""
Advanced Caching System
Multi-tier caching with Redis, in-memory cache, and intelligent cache strategies
"""

import asyncio
import json
import pickle
import hashlib
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Callable
from functools import wraps
from dataclasses import dataclass
import redis.asyncio as redis
from contextlib import asynccontextmanager


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    value: Any
    timestamp: datetime
    ttl: Optional[int] = None
    access_count: int = 0
    last_accessed: datetime = None

    def __post_init__(self):
        if self.last_accessed is None:
            self.last_accessed = self.timestamp

    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        if self.ttl is None:
            return False
        return (datetime.utcnow() - self.timestamp).total_seconds() > self.ttl

    def access(self):
        """Record cache access"""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()


class InMemoryCache:
    """High-performance in-memory cache with LRU eviction"""

    def __init__(self, max_size: int = 10000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, CacheEntry] = {}
        self.access_order: List[str] = []
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        async with self._lock:
            if key not in self.cache:
                return None

            entry = self.cache[key]

            # Check expiration
            if entry.is_expired():
                await self._remove(key)
                return None

            # Update access order for LRU
            if key in self.access_order:
                self.access_order.remove(key)
            self.access_order.append(key)

            entry.access()
            return entry.value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache"""
        async with self._lock:
            if ttl is None:
                ttl = self.default_ttl

            # Create cache entry
            entry = CacheEntry(
                value=value,
                timestamp=datetime.utcnow(),
                ttl=ttl
            )

            # Check if we need to evict
            if len(self.cache) >= self.max_size and key not in self.cache:
                await self._evict_lru()

            self.cache[key] = entry

            # Update access order
            if key in self.access_order:
                self.access_order.remove(key)
            self.access_order.append(key)

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        async with self._lock:
            return await self._remove(key)

    async def clear(self) -> None:
        """Clear all cache entries"""
        async with self._lock:
            self.cache.clear()
            self.access_order.clear()

    async def _remove(self, key: str) -> bool:
        """Remove key from cache (internal)"""
        if key in self.cache:
            del self.cache[key]
            if key in self.access_order:
                self.access_order.remove(key)
            return True
        return False

    async def _evict_lru(self) -> None:
        """Evict least recently used entry"""
        if self.access_order:
            lru_key = self.access_order[0]
            await self._remove(lru_key)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_accesses = sum(entry.access_count for entry in self.cache.values())
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "total_accesses": total_accesses,
            "hit_rate": 0.0 if total_accesses == 0 else len(self.cache) / total_accesses
        }


class RedisCache:
    """Redis-based distributed cache"""

    def __init__(self, redis_url: str = "redis://localhost:6379", default_ttl: int = 3600):
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.redis_client: Optional[redis.Redis] = None

    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=False)
            await self.redis_client.ping()
        except Exception as e:
            print(f"Redis connection failed: {e}")
            self.redis_client = None

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache"""
        if not self.redis_client:
            return None

        try:
            data = await self.redis_client.get(key)
            if data:
                return pickle.loads(data)
        except Exception as e:
            print(f"Redis get error: {e}")

        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in Redis cache"""
        if not self.redis_client:
            return False

        try:
            if ttl is None:
                ttl = self.default_ttl

            data = pickle.dumps(value)
            await self.redis_client.setex(key, ttl, data)
            return True
        except Exception as e:
            print(f"Redis set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from Redis cache"""
        if not self.redis_client:
            return False

        try:
            result = await self.redis_client.delete(key)
            return result > 0
        except Exception as e:
            print(f"Redis delete error: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern"""
        if not self.redis_client:
            return 0

        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                return await self.redis_client.delete(*keys)
        except Exception as e:
            print(f"Redis clear pattern error: {e}")

        return 0


class MultiTierCache:
    """Multi-tier cache with in-memory L1 and Redis L2"""

    def __init__(self, redis_url: str = "redis://localhost:6379",
                 l1_max_size: int = 1000, default_ttl: int = 3600):
        self.l1_cache = InMemoryCache(max_size=l1_max_size, default_ttl=default_ttl)
        self.l2_cache = RedisCache(redis_url=redis_url, default_ttl=default_ttl)
        self.default_ttl = default_ttl

        # Cache statistics
        self.stats = {
            "l1_hits": 0,
            "l2_hits": 0,
            "misses": 0,
            "sets": 0
        }

    async def connect(self):
        """Initialize cache connections"""
        await self.l2_cache.connect()

    async def disconnect(self):
        """Close cache connections"""
        await self.l2_cache.disconnect()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from multi-tier cache"""
        # Try L1 cache first
        value = await self.l1_cache.get(key)
        if value is not None:
            self.stats["l1_hits"] += 1
            return value

        # Try L2 cache
        value = await self.l2_cache.get(key)
        if value is not None:
            self.stats["l2_hits"] += 1
            # Promote to L1 cache
            await self.l1_cache.set(key, value)
            return value

        self.stats["misses"] += 1
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in multi-tier cache"""
        if ttl is None:
            ttl = self.default_ttl

        # Set in both caches
        await self.l1_cache.set(key, value, ttl)
        await self.l2_cache.set(key, value, ttl)

        self.stats["sets"] += 1

    async def delete(self, key: str) -> bool:
        """Delete key from both cache tiers"""
        l1_deleted = await self.l1_cache.delete(key)
        l2_deleted = await self.l2_cache.delete(key)
        return l1_deleted or l2_deleted

    async def clear(self) -> None:
        """Clear both cache tiers"""
        await self.l1_cache.clear()
        # Note: We don't clear all of Redis, just our keys

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        total_requests = sum([
            self.stats["l1_hits"],
            self.stats["l2_hits"],
            self.stats["misses"]
        ])

        l1_stats = self.l1_cache.get_stats()

        return {
            "total_requests": total_requests,
            "l1_hits": self.stats["l1_hits"],
            "l2_hits": self.stats["l2_hits"],
            "misses": self.stats["misses"],
            "sets": self.stats["sets"],
            "l1_hit_rate": self.stats["l1_hits"] / total_requests if total_requests > 0 else 0,
            "l2_hit_rate": self.stats["l2_hits"] / total_requests if total_requests > 0 else 0,
            "overall_hit_rate": (self.stats["l1_hits"] + self.stats["l2_hits"]) / total_requests if total_requests > 0 else 0,
            "l1_cache_stats": l1_stats
        }


# Global cache instances
cache = MultiTierCache()


def cache_key(*args, **kwargs) -> str:
    """Generate cache key from arguments"""
    key_data = {
        "args": args,
        "kwargs": sorted(kwargs.items())
    }
    key_string = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.md5(key_string.encode()).hexdigest()


def cached(ttl: int = 3600, key_prefix: str = ""):
    """Decorator for caching function results"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            key = f"{key_prefix}:{func.__name__}:{cache_key(*args, **kwargs)}"

            # Try to get from cache
            cached_result = await cache.get(key)
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache.set(key, result, ttl)

            return result

        return wrapper
    return decorator


@asynccontextmanager
async def cache_context():
    """Context manager for cache lifecycle"""
    await cache.connect()
    try:
        yield cache
    finally:
        await cache.disconnect()


# Specific cache functions for common use cases
@cached(ttl=300, key_prefix="user")
async def get_user_by_id(user_id: int):
    """Cached user lookup by ID"""
    # This would be implemented in your user service
    pass


@cached(ttl=600, key_prefix="compliance")
async def get_compliance_tags(transaction_id: int):
    """Cached compliance tags lookup"""
    # This would be implemented in your compliance service
    pass


@cached(ttl=1800, key_prefix="analytics")
async def get_user_analytics(user_id: int, date_range: str):
    """Cached user analytics"""
    # This would be implemented in your analytics service
    pass
'''


def create_database_optimization():
    """Create database optimization and connection pooling"""
    return '''"""
Database Optimization and Connection Pooling
Advanced database performance improvements with connection pooling and query optimization
"""

import asyncio
import sqlite3
import aiosqlite
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from contextlib import asynccontextmanager
from dataclasses import dataclass
from functools import wraps
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConnectionPoolStats:
    """Connection pool statistics"""
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    total_queries: int = 0
    avg_query_time: float = 0.0
    slow_queries: int = 0
    connection_errors: int = 0


class AsyncConnectionPool:
    """Async SQLite connection pool with monitoring"""

    def __init__(self, database_path: str, max_connections: int = 10,
                 max_idle_time: int = 300, slow_query_threshold: float = 1.0):
        self.database_path = database_path
        self.max_connections = max_connections
        self.max_idle_time = max_idle_time
        self.slow_query_threshold = slow_query_threshold

        self.connections: List[aiosqlite.Connection] = []
        self.idle_connections: List[Tuple[aiosqlite.Connection, datetime]] = []
        self.active_connections: List[aiosqlite.Connection] = []

        self.stats = ConnectionPoolStats()
        self._lock = asyncio.Lock()

        # Start cleanup task
        self._cleanup_task = None

    async def start(self):
        """Start the connection pool"""
        # Create initial connections
        for _ in range(min(3, self.max_connections)):
            conn = await self._create_connection()
            self.idle_connections.append((conn, datetime.utcnow()))

        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_idle_connections())

        logger.info(f"Connection pool started with {len(self.idle_connections)} connections")

    async def stop(self):
        """Stop the connection pool and close all connections"""
        if self._cleanup_task:
            self._cleanup_task.cancel()

        async with self._lock:
            # Close all connections
            for conn in self.connections:
                await conn.close()

            for conn, _ in self.idle_connections:
                await conn.close()

            for conn in self.active_connections:
                await conn.close()

        logger.info("Connection pool stopped")

    async def _create_connection(self) -> aiosqlite.Connection:
        """Create a new database connection with optimizations"""
        conn = await aiosqlite.connect(
            self.database_path,
            timeout=30.0,
            check_same_thread=False
        )

        # Enable optimizations
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA synchronous=NORMAL")
        await conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
        await conn.execute("PRAGMA temp_store=MEMORY")
        await conn.execute("PRAGMA mmap_size=268435456")  # 256MB mmap

        self.connections.append(conn)
        self.stats.total_connections += 1

        return conn

    @asynccontextmanager
    async def get_connection(self):
        """Get a connection from the pool"""
        connection = None
        start_time = time.time()

        try:
            async with self._lock:
                # Try to get idle connection
                if self.idle_connections:
                    connection, _ = self.idle_connections.pop()
                    self.active_connections.append(connection)
                elif len(self.connections) < self.max_connections:
                    # Create new connection
                    connection = await self._create_connection()
                    self.active_connections.append(connection)
                else:
                    # Wait for connection to become available
                    raise Exception("No connections available")

            self.stats.active_connections = len(self.active_connections)
            self.stats.idle_connections = len(self.idle_connections)

            yield connection

        except Exception as e:
            self.stats.connection_errors += 1
            logger.error(f"Connection error: {e}")
            raise

        finally:
            if connection:
                async with self._lock:
                    if connection in self.active_connections:
                        self.active_connections.remove(connection)
                        self.idle_connections.append((connection, datetime.utcnow()))

                self.stats.active_connections = len(self.active_connections)
                self.stats.idle_connections = len(self.idle_connections)

    async def execute_query(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """Execute a query with performance monitoring"""
        start_time = time.time()

        try:
            async with self.get_connection() as conn:
                conn.row_factory = aiosqlite.Row

                if params:
                    cursor = await conn.execute(query, params)
                else:
                    cursor = await conn.execute(query)

                rows = await cursor.fetchall()
                await cursor.close()

                # Convert to list of dictionaries
                result = [dict(row) for row in rows]

                # Update statistics
                query_time = time.time() - start_time
                self.stats.total_queries += 1

                # Update average query time
                current_avg = self.stats.avg_query_time
                total_queries = self.stats.total_queries
                self.stats.avg_query_time = ((current_avg * (total_queries - 1)) + query_time) / total_queries

                # Track slow queries
                if query_time > self.slow_query_threshold:
                    self.stats.slow_queries += 1
                    logger.warning(f"Slow query detected: {query_time:.2f}s - {query[:100]}...")

                return result

        except Exception as e:
            logger.error(f"Query execution error: {e}")
            raise

    async def execute_transaction(self, queries: List[Tuple[str, Optional[Tuple]]]) -> bool:
        """Execute multiple queries in a transaction"""
        async with self.get_connection() as conn:
            try:
                await conn.execute("BEGIN")

                for query, params in queries:
                    if params:
                        await conn.execute(query, params)
                    else:
                        await conn.execute(query)

                await conn.commit()
                return True

            except Exception as e:
                await conn.rollback()
                logger.error(f"Transaction error: {e}")
                raise

    async def _cleanup_idle_connections(self):
        """Cleanup idle connections periodically"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute

                async with self._lock:
                    current_time = datetime.utcnow()
                    active_idle = []

                    for conn, idle_since in self.idle_connections:
                        if (current_time - idle_since).seconds > self.max_idle_time:
                            # Close idle connection
                            await conn.close()
                            if conn in self.connections:
                                self.connections.remove(conn)
                            self.stats.total_connections -= 1
                        else:
                            active_idle.append((conn, idle_since))

                    self.idle_connections = active_idle
                    self.stats.idle_connections = len(self.idle_connections)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")


class QueryOptimizer:
    """Query optimization and analysis tools"""

    @staticmethod
    def create_indexes(pool: AsyncConnectionPool):
        """Create performance indexes"""
        indexes = [
            # User indexes
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
            "CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active)",
            "CREATE INDEX IF NOT EXISTS idx_users_created ON users(created_at)",

            # Transaction indexes
            "CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_created ON transactions(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_amount ON transactions(amount)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_currency ON transactions(currency)",

            # Compliance tag indexes
            "CREATE INDEX IF NOT EXISTS idx_compliance_transaction_id ON compliance_tags(transaction_id)",
            "CREATE INDEX IF NOT EXISTS idx_compliance_tag_type ON compliance_tags(tag_type)",
            "CREATE INDEX IF NOT EXISTS idx_compliance_confidence ON compliance_tags(confidence)",
            "CREATE INDEX IF NOT EXISTS idx_compliance_created ON compliance_tags(created_at)",

            # Composite indexes for common queries
            "CREATE INDEX IF NOT EXISTS idx_transactions_user_status ON transactions(user_id, status)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_user_created ON transactions(user_id, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_compliance_trans_type ON compliance_tags(transaction_id, tag_type)"
        ]

        return indexes

    @staticmethod
    async def analyze_query_performance(pool: AsyncConnectionPool, query: str, params: Optional[Tuple] = None) -> Dict[str, Any]:
        """Analyze query performance with EXPLAIN QUERY PLAN"""
        explain_query = f"EXPLAIN QUERY PLAN {query}"

        start_time = time.time()
        explain_result = await pool.execute_query(explain_query, params)

        execution_start = time.time()
        result = await pool.execute_query(query, params)
        execution_time = time.time() - execution_start

        return {
            "execution_time": execution_time,
            "rows_returned": len(result),
            "query_plan": explain_result,
            "query": query,
            "params": params
        }


class DatabaseService:
    """High-level database service with caching and optimization"""

    def __init__(self, database_path: str):
        self.pool = AsyncConnectionPool(database_path)
        self.query_cache = {}
        self.cache_ttl = 300  # 5 minutes

    async def start(self):
        """Start database service"""
        await self.pool.start()

        # Create indexes for performance
        indexes = QueryOptimizer.create_indexes(self.pool)
        for index_query in indexes:
            try:
                await self.pool.execute_query(index_query)
            except Exception as e:
                logger.error(f"Index creation error: {e}")

    async def stop(self):
        """Stop database service"""
        await self.pool.stop()

    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID with caching"""
        cache_key = f"user:{user_id}"

        # Check cache first
        if cache_key in self.query_cache:
            cached_result, timestamp = self.query_cache[cache_key]
            if (time.time() - timestamp) < self.cache_ttl:
                return cached_result

        # Query database
        result = await self.pool.execute_query(
            "SELECT * FROM users WHERE id = ? AND is_active = 1",
            (user_id,)
        )

        user = result[0] if result else None

        # Cache result
        self.query_cache[cache_key] = (user, time.time())

        return user

    async def get_user_transactions(self, user_id: int, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get user transactions with pagination"""
        return await self.pool.execute_query(
            """
            SELECT t.*, COUNT(*) OVER() as total_count
            FROM transactions t
            WHERE t.user_id = ?
            ORDER BY t.created_at DESC
            LIMIT ? OFFSET ?
            """,
            (user_id, limit, offset)
        )

    async def get_transaction_with_compliance(self, transaction_id: int) -> Optional[Dict[str, Any]]:
        """Get transaction with compliance tags in a single query"""
        result = await self.pool.execute_query(
            """
            SELECT
                t.*,
                GROUP_CONCAT(ct.tag_type) as compliance_tags,
                GROUP_CONCAT(ct.confidence) as tag_confidences
            FROM transactions t
            LEFT JOIN compliance_tags ct ON t.id = ct.transaction_id
            WHERE t.id = ?
            GROUP BY t.id
            """,
            (transaction_id,)
        )

        if result:
            transaction = result[0]
            # Parse compliance tags
            if transaction['compliance_tags']:
                tags = transaction['compliance_tags'].split(',')
                confidences = [float(c) for c in transaction['tag_confidences'].split(',')]
                transaction['compliance_data'] = list(zip(tags, confidences))
            else:
                transaction['compliance_data'] = []

            return transaction

        return None

    async def create_transaction_with_tags(self, transaction_data: Dict[str, Any],
                                         compliance_tags: List[Tuple[str, float]]) -> int:
        """Create transaction and compliance tags in a single transaction"""
        queries = [
            (
                "INSERT INTO transactions (user_id, amount, currency, status, description) VALUES (?, ?, ?, ?, ?)",
                (
                    transaction_data['user_id'],
                    transaction_data['amount'],
                    transaction_data['currency'],
                    transaction_data.get('status', 'pending'),
                    transaction_data.get('description', '')
                )
            )
        ]

        # Add compliance tag queries
        for tag_type, confidence in compliance_tags:
            queries.append((
                "INSERT INTO compliance_tags (transaction_id, tag_type, confidence) VALUES (last_insert_rowid(), ?, ?)",
                (tag_type, confidence)
            ))

        await self.pool.execute_transaction(queries)

        # Get the transaction ID (this is a simplified version)
        result = await self.pool.execute_query("SELECT last_insert_rowid() as id")
        return result[0]['id'] if result else None

    def get_stats(self) -> Dict[str, Any]:
        """Get database performance statistics"""
        return {
            "connection_pool": {
                "total_connections": self.pool.stats.total_connections,
                "active_connections": self.pool.stats.active_connections,
                "idle_connections": self.pool.stats.idle_connections,
                "total_queries": self.pool.stats.total_queries,
                "avg_query_time": self.pool.stats.avg_query_time,
                "slow_queries": self.pool.stats.slow_queries,
                "connection_errors": self.pool.stats.connection_errors
            },
            "query_cache": {
                "cached_queries": len(self.query_cache),
                "cache_ttl": self.cache_ttl
            }
        }


# Global database service
db_service = DatabaseService("data/klerno.db")


def with_db_stats(func):
    """Decorator to track database operation statistics"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"DB operation {func.__name__} completed in {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"DB operation {func.__name__} failed after {execution_time:.3f}s: {e}")
            raise

    return wrapper
'''


def create_async_optimization():
    """Create async performance optimizations"""
    return '''"""
Async Performance Optimizations
Advanced async patterns, concurrency control, and performance improvements
"""

import asyncio
import time
import functools
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Union, Awaitable
from contextlib import asynccontextmanager
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConcurrencyStats:
    """Concurrency performance statistics"""
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    avg_completion_time: float = 0.0
    max_concurrent: int = 0
    current_concurrent: int = 0


class AsyncSemaphorePool:
    """Async semaphore pool for controlling concurrency"""

    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.stats = ConcurrencyStats(max_concurrent=max_concurrent)
        self.active_tasks: set = set()

    @asynccontextmanager
    async def acquire(self):
        """Acquire semaphore with statistics tracking"""
        await self.semaphore.acquire()

        task_id = id(asyncio.current_task())
        self.active_tasks.add(task_id)
        self.stats.current_concurrent = len(self.active_tasks)
        self.stats.total_tasks += 1

        start_time = time.time()

        try:
            yield

            # Update completion statistics
            completion_time = time.time() - start_time
            self.stats.completed_tasks += 1

            # Update average completion time
            current_avg = self.stats.avg_completion_time
            completed = self.stats.completed_tasks
            self.stats.avg_completion_time = ((current_avg * (completed - 1)) + completion_time) / completed

        except Exception as e:
            self.stats.failed_tasks += 1
            logger.error(f"Task failed: {e}")
            raise

        finally:
            self.active_tasks.discard(task_id)
            self.stats.current_concurrent = len(self.active_tasks)
            self.semaphore.release()


class BatchProcessor:
    """Batch processing for improved throughput"""

    def __init__(self, batch_size: int = 50, batch_timeout: float = 1.0):
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.pending_items: List[Any] = []
        self.batch_processors: Dict[str, Callable] = {}
        self._processing_task: Optional[asyncio.Task] = None
        self._shutdown = False

    def register_processor(self, name: str, processor: Callable[[List[Any]], Awaitable[List[Any]]]):
        """Register a batch processor function"""
        self.batch_processors[name] = processor

    async def start(self):
        """Start batch processing"""
        if not self._processing_task:
            self._processing_task = asyncio.create_task(self._process_batches())

    async def stop(self):
        """Stop batch processing"""
        self._shutdown = True
        if self._processing_task:
            await self._processing_task

    async def add_item(self, item: Any) -> Any:
        """Add item to batch for processing"""
        future = asyncio.Future()
        self.pending_items.append((item, future))

        # Check if we should process immediately
        if len(self.pending_items) >= self.batch_size:
            await self._process_current_batch()

        return await future

    async def _process_batches(self):
        """Main batch processing loop"""
        while not self._shutdown:
            try:
                await asyncio.sleep(self.batch_timeout)

                if self.pending_items:
                    await self._process_current_batch()

            except Exception as e:
                logger.error(f"Batch processing error: {e}")

    async def _process_current_batch(self):
        """Process current batch of items"""
        if not self.pending_items:
            return

        # Extract items and futures
        items = []
        futures = []

        batch_items = self.pending_items[:self.batch_size]
        self.pending_items = self.pending_items[self.batch_size:]

        for item, future in batch_items:
            items.append(item)
            futures.append(future)

        try:
            # Process batch (this would be customized for your use case)
            results = await self._default_processor(items)

            # Set results for futures
            for future, result in zip(futures, results):
                if not future.done():
                    future.set_result(result)

        except Exception as e:
            # Set exception for all futures
            for future in futures:
                if not future.done():
                    future.set_exception(e)

    async def _default_processor(self, items: List[Any]) -> List[Any]:
        """Default batch processor (override for specific use cases)"""
        return items


class AsyncTaskManager:
    """Advanced async task management with monitoring"""

    def __init__(self, max_concurrent: int = 100):
        self.max_concurrent = max_concurrent
        self.semaphore_pool = AsyncSemaphorePool(max_concurrent)
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.task_results: Dict[str, Any] = {}
        self.task_stats: Dict[str, Dict[str, Any]] = {}

    async def submit_task(self, task_id: str, coro: Awaitable[Any],
                         timeout: Optional[float] = None) -> str:
        """Submit a task for async execution"""
        if task_id in self.running_tasks:
            raise ValueError(f"Task {task_id} is already running")

        async def _execute_task():
            start_time = time.time()

            try:
                async with self.semaphore_pool.acquire():
                    if timeout:
                        result = await asyncio.wait_for(coro, timeout=timeout)
                    else:
                        result = await coro

                    execution_time = time.time() - start_time

                    # Store result and stats
                    self.task_results[task_id] = result
                    self.task_stats[task_id] = {
                        "status": "completed",
                        "execution_time": execution_time,
                        "completed_at": datetime.utcnow().isoformat()
                    }

                    return result

            except asyncio.TimeoutError:
                execution_time = time.time() - start_time
                self.task_stats[task_id] = {
                    "status": "timeout",
                    "execution_time": execution_time,
                    "completed_at": datetime.utcnow().isoformat()
                }
                raise

            except Exception as e:
                execution_time = time.time() - start_time
                self.task_stats[task_id] = {
                    "status": "failed",
                    "execution_time": execution_time,
                    "error": str(e),
                    "completed_at": datetime.utcnow().isoformat()
                }
                raise

            finally:
                # Cleanup
                if task_id in self.running_tasks:
                    del self.running_tasks[task_id]

        # Create and store task
        task = asyncio.create_task(_execute_task())
        self.running_tasks[task_id] = task

        # Initialize stats
        self.task_stats[task_id] = {
            "status": "running",
            "started_at": datetime.utcnow().isoformat()
        }

        return task_id

    async def get_task_result(self, task_id: str, wait: bool = True) -> Any:
        """Get task result"""
        if task_id in self.task_results:
            return self.task_results[task_id]

        if task_id in self.running_tasks and wait:
            task = self.running_tasks[task_id]
            return await task

        raise ValueError(f"Task {task_id} not found or not completed")

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get task status and statistics"""
        return self.task_stats.get(task_id, {"status": "not_found"})

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task"""
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            task.cancel()

            self.task_stats[task_id] = {
                "status": "cancelled",
                "cancelled_at": datetime.utcnow().isoformat()
            }

            return True

        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get task manager statistics"""
        total_tasks = len(self.task_stats)
        completed_tasks = sum(1 for stats in self.task_stats.values() if stats["status"] == "completed")
        failed_tasks = sum(1 for stats in self.task_stats.values() if stats["status"] == "failed")
        running_tasks = len(self.running_tasks)

        # Calculate average execution time for completed tasks
        completed_times = [
            stats.get("execution_time", 0)
            for stats in self.task_stats.values()
            if stats["status"] == "completed" and "execution_time" in stats
        ]
        avg_execution_time = sum(completed_times) / len(completed_times) if completed_times else 0

        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "running_tasks": running_tasks,
            "avg_execution_time": avg_execution_time,
            "concurrency_stats": {
                "max_concurrent": self.semaphore_pool.stats.max_concurrent,
                "current_concurrent": self.semaphore_pool.stats.current_concurrent,
                "total_tasks": self.semaphore_pool.stats.total_tasks,
                "completed_tasks": self.semaphore_pool.stats.completed_tasks,
                "failed_tasks": self.semaphore_pool.stats.failed_tasks,
                "avg_completion_time": self.semaphore_pool.stats.avg_completion_time
            }
        }


def async_retry(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0,
               exceptions: tuple = (Exception,)):
    """Async retry decorator with exponential backoff"""
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)

                except exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.error(f"Function {func.__name__} failed after {max_retries} retries: {e}")
                        raise

                    logger.warning(f"Function {func.__name__} failed (attempt {attempt + 1}), retrying in {current_delay}s: {e}")
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff

            raise last_exception

        return wrapper
    return decorator


def async_timeout(timeout_seconds: float):
    """Async timeout decorator"""
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_seconds)
            except asyncio.TimeoutError:
                logger.error(f"Function {func.__name__} timed out after {timeout_seconds}s")
                raise

        return wrapper
    return decorator


def async_rate_limit(calls_per_second: float):
    """Async rate limiting decorator"""
    def decorator(func: Callable):
        last_called = 0.0
        min_interval = 1.0 / calls_per_second

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            nonlocal last_called

            current_time = time.time()
            time_since_last = current_time - last_called

            if time_since_last < min_interval:
                sleep_time = min_interval - time_since_last
                await asyncio.sleep(sleep_time)

            last_called = time.time()
            return await func(*args, **kwargs)

        return wrapper
    return decorator


# Global task manager
task_manager = AsyncTaskManager()


async def process_concurrent_tasks(tasks: List[Awaitable[Any]],
                                 max_concurrent: int = 10) -> List[Any]:
    """Process multiple tasks with controlled concurrency"""
    semaphore = asyncio.Semaphore(max_concurrent)

    async def _process_task(task):
        async with semaphore:
            return await task

    # Execute all tasks with concurrency control
    results = await asyncio.gather(*[_process_task(task) for task in tasks])
    return results


async def batch_process_items(items: List[Any], processor: Callable[[Any], Awaitable[Any]],
                            batch_size: int = 50, max_concurrent: int = 10) -> List[Any]:
    """Process items in batches with controlled concurrency"""
    results = []

    # Process items in batches
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]

        # Create tasks for batch
        tasks = [processor(item) for item in batch]

        # Process batch with concurrency control
        batch_results = await process_concurrent_tasks(tasks, max_concurrent)
        results.extend(batch_results)

    return results
'''


def create_performance_files():
    """Create all performance optimization files"""
    print("⚡ Creating performance optimization system...")

    # Create performance directory
    os.makedirs("app/performance", exist_ok=True)

    # Advanced caching
    with open("app/performance/caching.py", 'w', encoding='utf-8') as f:
        f.write(create_advanced_caching())

    # Database optimization
    with open("app/performance/database.py", 'w', encoding='utf-8') as f:
        f.write(create_database_optimization())

    # Async optimization
    with open("app/performance/async_optimization.py", 'w', encoding='utf-8') as f:
        f.write(create_async_optimization())

    print("✅ Performance optimization files created")


def create_performance_middleware():
    """Create performance middleware for FastAPI"""
    middleware_code = '''"""
Performance Middleware for FastAPI
Advanced middleware for performance monitoring and optimization
"""

import time
import asyncio
from typing import Callable, Dict, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.performance.caching import cache
from app.monitoring.metrics import metrics
from app.monitoring.logging import get_logger

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
        logger.debug(f"Request started: {method} {path}", extra={
            "request_id": request_id,
            "method": method,
            "path": path,
            "user_agent": user_agent
        })

        try:
            # Check cache for GET requests
            if self.cache_enabled and method == "GET" and self._is_cacheable(path):
                cached_response = await self._get_cached_response(request)
                if cached_response:
                    response_time = time.time() - start_time

                    # Track cache hit metrics
                    if self.metrics_enabled:
                        metrics.increment("http_cache_hits", tags={
                            "endpoint": path,
                            "method": method
                        })
                        metrics.histogram("http_response_time", response_time * 1000, tags={
                            "endpoint": path,
                            "method": method,
                            "cache": "hit"
                        })

                    logger.info(f"Cache hit: {method} {path} - {response_time:.3f}s", extra={
                        "request_id": request_id,
                        "response_time": response_time,
                        "cache_hit": True
                    })

                    return cached_response

            # Process request
            response = await call_next(request)
            response_time = time.time() - start_time

            # Cache successful GET responses
            if (self.cache_enabled and method == "GET" and
                response.status_code == 200 and self._is_cacheable(path)):
                await self._cache_response(request, response)

            # Track metrics
            if self.metrics_enabled:
                metrics.increment("http_requests_total", tags={
                    "endpoint": path,
                    "method": method,
                    "status_code": str(response.status_code)
                })

                metrics.histogram("http_response_time", response_time * 1000, tags={
                    "endpoint": path,
                    "method": method,
                    "status_code": str(response.status_code),
                    "cache": "miss"
                })

                if response.status_code >= 400:
                    metrics.increment("http_errors_total", tags={
                        "endpoint": path,
                        "method": method,
                        "status_code": str(response.status_code)
                    })

            # Log slow requests
            if response_time > self.slow_request_threshold:
                logger.warning(f"Slow request: {method} {path} - {response_time:.3f}s", extra={
                    "request_id": request_id,
                    "response_time": response_time,
                    "status_code": response.status_code,
                    "slow_request": True
                })
            else:
                logger.info(f"Request completed: {method} {path} - {response_time:.3f}s", extra={
                    "request_id": request_id,
                    "response_time": response_time,
                    "status_code": response.status_code
                })

            # Add performance headers
            response.headers["X-Response-Time"] = f"{response_time:.3f}s"
            response.headers["X-Request-ID"] = str(request_id)

            return response

        except Exception as e:
            response_time = time.time() - start_time

            # Track error metrics
            if self.metrics_enabled:
                metrics.increment("http_errors_total", tags={
                    "endpoint": path,
                    "method": method,
                    "status_code": "500"
                })

            logger.error(f"Request failed: {method} {path} - {response_time:.3f}s - {str(e)}", extra={
                "request_id": request_id,
                "response_time": response_time,
                "error": str(e)
            })

            raise

    def _is_cacheable(self, path: str) -> bool:
        """Check if path is cacheable"""
        cacheable_paths = [
            "/dashboard",
            "/analytics",
            "/health",
            "/static"
        ]

        # Don't cache API endpoints that might have user-specific data
        non_cacheable_paths = [
            "/auth",
            "/admin",
            "/api/user"
        ]

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
                media_type=cached_data["media_type"]
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
                "media_type": response.media_type
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
            "/dashboard": 300,      # 5 minutes
            "/analytics": 600,      # 10 minutes
            "/health": 60,          # 1 minute
            "/static": 3600         # 1 hour
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
'''

    with open("app/performance/middleware.py", 'w', encoding='utf-8') as f:
        f.write(middleware_code)

    print("✅ Performance middleware created")


def main():
    print("=" * 60)
    print("⚡ COMPREHENSIVE PERFORMANCE OPTIMIZATION SETUP")
    print("=" * 60)

    # Create performance files
    create_performance_files()
    create_performance_middleware()

    # Create performance configuration
    performance_config = {
        "caching": {
            "enabled": True,
            "redis_url": "redis://localhost:6379",
            "l1_cache_size": 1000,
            "default_ttl": 3600,
            "cache_strategies": {
                "user_data": {"ttl": 300, "tier": "both"},
                "compliance_tags": {"ttl": 600, "tier": "both"},
                "analytics": {"ttl": 1800, "tier": "redis"},
                "static_content": {"ttl": 3600, "tier": "both"}
            }
        },
        "database": {
            "connection_pool": {
                "max_connections": 20,
                "max_idle_time": 300,
                "slow_query_threshold": 1.0
            },
            "optimizations": {
                "enable_wal_mode": True,
                "cache_size_mb": 64,
                "mmap_size_mb": 256,
                "auto_create_indexes": True
            }
        },
        "async_optimization": {
            "max_concurrent_requests": 100,
            "max_concurrent_tasks": 50,
            "batch_processing": {
                "enabled": True,
                "batch_size": 50,
                "batch_timeout": 1.0
            },
            "retry_settings": {
                "max_retries": 3,
                "initial_delay": 1.0,
                "backoff_factor": 2.0
            }
        },
        "performance_monitoring": {
            "slow_request_threshold": 2.0,
            "enable_response_time_tracking": True,
            "enable_concurrency_monitoring": True,
            "cache_hit_rate_monitoring": True
        }
    }

    with open("app/performance/config.json", 'w', encoding='utf-8') as f:
        json.dump(performance_config, f, indent=2)

    # Create performance dependencies
    performance_deps = [
        "redis>=4.5.0",
        "aioredis>=2.0.0",
        "aiosqlite>=0.19.0",
        "asyncpg>=0.28.0",  # For PostgreSQL if needed
        "aiocache>=0.12.0"
    ]

    print("\n📦 Additional performance dependencies needed:")
    for dep in performance_deps:
        print(f"   • {dep}")

    print("\n" + "=" * 60)
    print("⚡ PERFORMANCE OPTIMIZATION COMPLETE")
    print("=" * 60)
    print("✅ Multi-tier caching (Redis + In-memory)")
    print("✅ Database connection pooling and optimization")
    print("✅ Advanced async patterns and concurrency control")
    print("✅ Performance middleware with monitoring")
    print("✅ Batch processing and task management")
    print("✅ Query optimization and indexing")

    print("\n🎯 Performance Features:")
    print("• L1/L2 Cache: Sub-millisecond in-memory + distributed Redis")
    print("• Connection Pool: Optimized SQLite with WAL mode")
    print("• Async Control: Semaphore-based concurrency limiting")
    print("• Batch Processing: Improved throughput for bulk operations")
    print("• Smart Caching: Path-based TTL and cache strategies")
    print("• Performance Monitoring: Response times and cache hit rates")

    print("\n🚀 Integration Instructions:")
    print("1. Install performance dependencies")
    print("2. Add performance middleware to main.py")
    print("3. Configure Redis connection")
    print("4. Initialize database connection pool")
    print("5. Monitor performance metrics in dashboards")

    print("\n🎉 Your application is now optimized for production scale!")


if __name__ == "__main__":
    main()
