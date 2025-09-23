"""
Database Optimization and Connection Pooling
Advanced database performance improvements with connection pooling and query optimization
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from typing import Any

import aiosqlite

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

    def __init__(
        self,
        database_path: str,
        max_connections: int = 10,
        max_idle_time: int = 300,
        slow_query_threshold: float = 1.0,
    ):
        self.database_path = database_path
        self.max_connections = max_connections
        self.max_idle_time = max_idle_time
        self.slow_query_threshold = slow_query_threshold

        self.connections: list[aiosqlite.Connection] = []
        self.idle_connections: list[tuple[aiosqlite.Connection, datetime]] = []
        self.active_connections: list[aiosqlite.Connection] = []

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

        logger.info(
            f"Connection pool started with {len(self.idle_connections)} connections"
        )

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
            self.database_path, timeout=30.0, check_same_thread=False
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
        time.time()

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

    async def execute_query(
        self, query: str, params: tuple | None = None
    ) -> list[dict[str, Any]]:
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
                self.stats.avg_query_time = (
                    (current_avg * (total_queries - 1)) + query_time
                ) / total_queries

                # Track slow queries
                if query_time > self.slow_query_threshold:
                    self.stats.slow_queries += 1
                    logger.warning(
                        f"Slow query detected: {query_time:.2f}s - {query[:100]}..."
                    )

                return result

        except Exception as e:
            logger.error(f"Query execution error: {e}")
            raise

    async def execute_transaction(
        self, queries: list[tuple[str, tuple | None]]
    ) -> bool:
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
            ("CREATE INDEX IF NOT EXISTS idx_users_email " "ON users(email)"),
            ("CREATE INDEX IF NOT EXISTS idx_users_active " "ON users(is_active)"),
            ("CREATE INDEX IF NOT EXISTS idx_users_created " "ON users(created_at)"),
            # Transaction indexes
            (
                "CREATE INDEX IF NOT EXISTS idx_transactions_user_id "
                "ON transactions(user_id)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS idx_transactions_status "
                "ON transactions(status)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS idx_transactions_created "
                "ON transactions(created_at)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS idx_transactions_amount "
                "ON transactions(amount)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS idx_transactions_currency "
                "ON transactions(currency)"
            ),
            # Compliance tag indexes
            (
                "CREATE INDEX IF NOT EXISTS idx_compliance_transaction_id "
                "ON compliance_tags(transaction_id)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS idx_compliance_tag_type "
                "ON compliance_tags(tag_type)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS idx_compliance_confidence "
                "ON compliance_tags(confidence)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS idx_compliance_created "
                "ON compliance_tags(created_at)"
            ),
            # Composite indexes for common queries
            (
                "CREATE INDEX IF NOT EXISTS idx_transactions_user_status "
                "ON transactions(user_id, status)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS idx_transactions_user_created "
                "ON transactions(user_id, created_at)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS idx_compliance_trans_type "
                "ON compliance_tags(transaction_id, tag_type)"
            ),
        ]

        return indexes

    @staticmethod
    async def analyze_query_performance(
        pool: AsyncConnectionPool, query: str, params: tuple | None = None
    ) -> dict[str, Any]:
        """Analyze query performance with EXPLAIN QUERY PLAN"""
        explain_query = f"EXPLAIN QUERY PLAN {query}"

        time.time()
        explain_result = await pool.execute_query(explain_query, params)

        execution_start = time.time()
        result = await pool.execute_query(query, params)
        execution_time = time.time() - execution_start

        return {
            "execution_time": execution_time,
            "rows_returned": len(result),
            "query_plan": explain_result,
            "query": query,
            "params": params,
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

    async def get_user_by_id(self, user_id: int) -> dict[str, Any] | None:
        """Get user by ID with caching"""
        cache_key = f"user:{user_id}"

        # Check cache first
        if cache_key in self.query_cache:
            cached_result, timestamp = self.query_cache[cache_key]
            if (time.time() - timestamp) < self.cache_ttl:
                return cached_result

        # Query database
        result = await self.pool.execute_query(
            "SELECT * FROM users WHERE id = ? AND is_active = 1", (user_id,)
        )

        user = result[0] if result else None

        # Cache result
        self.query_cache[cache_key] = (user, time.time())

        return user

    async def get_user_transactions(
        self, user_id: int, limit: int = 100, offset: int = 0
    ) -> list[dict[str, Any]]:
        """Get user transactions with pagination"""
        return await self.pool.execute_query(
            """
            SELECT t.*, COUNT(*) OVER() as total_count
            FROM transactions t
            WHERE t.user_id = ?
            ORDER BY t.created_at DESC
            LIMIT ? OFFSET ?
            """,
            (user_id, limit, offset),
        )

    async def get_transaction_with_compliance(
        self, transaction_id: int
    ) -> dict[str, Any] | None:
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
            (transaction_id,),
        )

        if result:
            transaction = result[0]
            # Parse compliance tags
            if transaction["compliance_tags"]:
                tags = transaction["compliance_tags"].split(",")
                confidences = [
                    float(c) for c in transaction["tag_confidences"].split(",")
                ]
                transaction["compliance_data"] = list(
                    zip(tags, confidences, strict=False)
                )
            else:
                transaction["compliance_data"] = []

            return transaction

        return None

    async def create_transaction_with_tags(
        self,
        transaction_data: dict[str, Any],
        compliance_tags: list[tuple[str, float]],
    ) -> int | None:
        """Create transaction and compliance tags in a single transaction"""
        queries: list[tuple[str, tuple[Any, ...] | None]] = [
            (
                (
                    "INSERT INTO transactions (user_id, amount, currency, "
                    "status, description) VALUES (?, ?, ?, ?, ?)"
                ),
                (
                    transaction_data["user_id"],
                    transaction_data["amount"],
                    transaction_data["currency"],
                    transaction_data.get("status", "pending"),
                    transaction_data.get("description", ""),
                ),
            )
        ]

        # Add compliance tag queries
        for tag_type, confidence in compliance_tags:
            queries.append(
                (
                    (
                        "INSERT INTO compliance_tags (transaction_id, "
                        "tag_type, confidence) "
                        "VALUES (last_insert_rowid(), ?, ?)"
                    ),
                    (tag_type, confidence),
                )
            )

        await self.pool.execute_transaction(queries)

        # Get the transaction ID (this is a simplified version)
        result = await self.pool.execute_query("SELECT last_insert_rowid() as id")
        return result[0]["id"] if result else None

    def get_stats(self) -> dict[str, Any]:
        """Get database performance statistics"""
        return {
            "connection_pool": {
                "total_connections": self.pool.stats.total_connections,
                "active_connections": self.pool.stats.active_connections,
                "idle_connections": self.pool.stats.idle_connections,
                "total_queries": self.pool.stats.total_queries,
                "avg_query_time": self.pool.stats.avg_query_time,
                "slow_queries": self.pool.stats.slow_queries,
                "connection_errors": self.pool.stats.connection_errors,
            },
            "query_cache": {
                "cached_queries": len(self.query_cache),
                "cache_ttl": self.cache_ttl,
            },
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
            logger.info(
                f"DB operation {func.__name__} completed in " f"{execution_time:.3f}s"
            )
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"DB operation {func.__name__} failed after "
                f"{execution_time:.3f}s: {e}"
            )
            raise

    return wrapper
