"""Klerno Labs Enterprise Database Connection Pool & Async Processing
Advanced database management with connection pooling and async operations.
"""

import asyncio
import logging
import queue
import sqlite3
import threading
import time
import weakref
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from app._typing_shims import ISyncConnection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ConnectionStats:
    """Connection pool statistics."""

    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    failed_connections: int = 0
    total_queries: int = 0
    avg_query_time: float = 0.0
    peak_connections: int = 0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class AsyncTask:
    """Async task definition."""

    task_id: str
    function: Callable
    args: tuple[Any, ...] = field(default_factory=tuple[Any, ...])
    kwargs: dict[str, Any] = field(default_factory=dict[str, Any])
    priority: int = 5  # 1=highest, 10=lowest
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.now)
    scheduled_at: datetime | None = None


class DatabaseConnectionPool:
    """Enterprise-grade database connection pool."""

    def __init__(
        self,
        database_path: str = "./data/klerno.db",
        pool_size: int = 20,
        max_overflow: int = 10,
        timeout: int = 30,
        recycle_time: int = 3600,
    ) -> None:
        self.database_path = database_path
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.timeout = timeout
        self.recycle_time = recycle_time

        # Connection management
        self._pool: queue.Queue[tuple[ISyncConnection, float]] = queue.Queue(
            maxsize=pool_size,
        )
        self._overflow: list[ISyncConnection] = []
        self._checked_out: weakref.WeakSet[ISyncConnection] = weakref.WeakSet()
        self._stats: ConnectionStats = ConnectionStats()
        self._lock: threading.RLock = threading.RLock()

        # Initialize pool
        self._initialize_pool()

        # Start maintenance thread
        self._maintenance_thread: threading.Thread = threading.Thread(
            target=self._maintenance_worker,
            daemon=True,
        )
        self._maintenance_thread.start()

        logger.info(
            f"[DB-POOL] Initialized with {pool_size} connections, max overflow: {max_overflow}",
        )

    def _initialize_pool(self) -> None:
        """Initialize the connection pool."""
        try:
            # Ensure database directory exists
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)

            # Create initial connections
            for _i in range(self.pool_size):
                try:
                    conn = self._create_connection()
                    if conn is not None:
                        # Put the runtime sqlite3.Connection into the pool; the ISyncConnection
                        # protocol describes the expected attributes at type-check time.
                        self._pool.put((conn, time.time()))
                        self._stats.total_connections += 1
                except RuntimeError:
                    # skip failed connection creation
                    continue

            logger.info(
                f"[DB-POOL] Created {self._stats.total_connections} initial connections",
            )

        except Exception as e:
            logger.exception(f"[DB-POOL] Failed to initialize pool: {e}")

    def _create_connection(self) -> ISyncConnection | None:
        """Create a new database connection."""
        try:
            conn = sqlite3.connect(
                self.database_path,
                timeout=self.timeout,
                check_same_thread=False,
            )

            # Configure connection
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            conn.execute("PRAGMA temp_store=MEMORY")
            conn.execute("PRAGMA mmap_size=268435456")  # 256MB

            from typing import cast

            return cast("ISyncConnection", conn)

        except Exception as e:
            logger.exception(f"[DB-POOL] Failed to create connection: {e}")
            self._stats.failed_connections += 1
            msg = f"Failed to create DB connection: {e}"
            raise RuntimeError(msg) from e

    def get_connection(self) -> ISyncConnection | None:
        """Get a connection from the pool."""
        start_time = time.time()

        try:
            with self._lock:
                # Try to get from pool
                try:
                    conn, created_at = self._pool.get_nowait()

                    # Check if connection needs recycling
                    if time.time() - created_at > self.recycle_time:
                        conn.close()
                        new_conn = self._create_connection()
                        if not new_conn:
                            return None
                        conn = new_conn

                    self._checked_out.add(conn)
                    self._stats.active_connections += 1
                    return conn

                except queue.Empty:
                    # Pool is empty, try overflow
                    if len(self._overflow) < self.max_overflow:
                        try:
                            new_conn = self._create_connection()
                        except RuntimeError:
                            new_conn = None

                        if new_conn:
                            self._overflow.append(new_conn)
                            self._checked_out.add(new_conn)
                            self._stats.active_connections += 1
                            self._stats.total_connections += 1
                            return new_conn

                    logger.warning("[DB-POOL] Pool exhausted, no connections available")
                    return None

        except Exception as e:
            logger.exception(f"[DB-POOL] Error getting connection: {e}")
            return None

        finally:
            # Update stats
            query_time = time.time() - start_time
            self._stats.total_queries += 1
            self._stats.avg_query_time = (
                self._stats.avg_query_time * (self._stats.total_queries - 1)
                + query_time
            ) / self._stats.total_queries

            self._stats.peak_connections = max(
                self._stats.peak_connections,
                self._stats.active_connections,
            )

    def return_connection(self, conn: ISyncConnection) -> None:
        """Return a connection to the pool."""
        if not conn:
            return

        try:
            with self._lock:
                self._checked_out.discard(conn)
                self._stats.active_connections = max(
                    0,
                    self._stats.active_connections - 1,
                )

                # Check if it's an overflow connection
                if conn in self._overflow:
                    self._overflow.remove(conn)
                    conn.close()
                    self._stats.total_connections -= 1
                else:
                    # Return to pool
                    try:
                        self._pool.put_nowait((conn, time.time()))
                    except queue.Full:
                        # Pool is full, close connection
                        conn.close()
                        self._stats.total_connections -= 1

        except Exception as e:
            logger.exception(f"[DB-POOL] Error returning connection: {e}")

    def _maintenance_worker(self) -> None:
        """Background maintenance of connections."""
        while True:
            try:
                time.sleep(300)  # Run every 5 minutes

                with self._lock:
                    # Clean up stale connections
                    current_time = time.time()
                    temp_pool = []

                    while not self._pool.empty():
                        try:
                            conn, created_at = self._pool.get_nowait()

                            if current_time - created_at > self.recycle_time:
                                conn.close()
                                # Create new connection
                                new_conn = self._create_connection()
                                if new_conn:
                                    temp_pool.append((new_conn, current_time))
                            else:
                                temp_pool.append((conn, created_at))

                        except queue.Empty:
                            break

                    # Put connections back
                    for conn_tuple in temp_pool:
                        try:
                            self._pool.put_nowait(conn_tuple)
                        except queue.Full:
                            conn_tuple[0].close()

                    # Update idle connections count
                    self._stats.idle_connections = self._pool.qsize()

                logger.info(
                    f"[DB-POOL] Maintenance: {self._stats.active_connections} active, "
                    f"{self._stats.idle_connections} idle, {self._stats.total_connections} total",
                )

            except Exception as e:
                logger.exception(f"[DB-POOL] Maintenance error: {e}")

    def get_stats(self) -> ConnectionStats:
        """Get connection pool statistics."""
        with self._lock:
            self._stats.idle_connections = self._pool.qsize()
            return self._stats

    def close_all(self) -> None:
        """Close all connections."""
        with self._lock:
            # Close pool connections
            while not self._pool.empty():
                try:
                    conn, _ = self._pool.get_nowait()
                    conn.close()
                except queue.Empty:
                    break

            # Close overflow connections
            for conn in self._overflow:
                conn.close()

            self._overflow.clear()

            logger.info("[DB-POOL] All connections closed")


class AsyncTaskProcessor:
    """Enterprise async task processing system."""

    def __init__(
        self,
        max_workers: int = 10,
        queue_size: int = 1000,
        batch_size: int = 50,
    ) -> None:
        self.max_workers = max_workers
        self.queue_size = queue_size
        self.batch_size = batch_size

        # Task management
        self._task_queue: queue.PriorityQueue[tuple[int, float, AsyncTask]] = (
            queue.PriorityQueue(maxsize=queue_size)
        )
        self._scheduled_tasks: list[AsyncTask] = []
        self._completed_tasks: list[tuple[AsyncTask, Any]] = []
        self._failed_tasks: list[tuple[AsyncTask, Exception]] = []

        # Threading
        self._executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=max_workers)
        self._scheduler_thread: threading.Thread = threading.Thread(
            target=self._scheduler_worker,
            daemon=True,
        )
        self._processor_thread: threading.Thread = threading.Thread(
            target=self._processor_worker,
            daemon=True,
        )

        # Statistics
        self._stats: dict[str, Any] = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "queued_tasks": 0,
            "processing_tasks": 0,
            "avg_processing_time": 0.0,
        }

        self._lock: threading.RLock = threading.RLock()
        self._running: bool = True

        # Start workers
        self._scheduler_thread.start()
        self._processor_thread.start()

        logger.info(f"[ASYNC] Task processor started with {max_workers} workers")

    def submit_task(self, task: AsyncTask) -> str | None:
        """Submit a task for async processing."""
        try:
            with self._lock:
                if self._task_queue.qsize() >= self.queue_size:
                    logger.warning("[ASYNC] Task queue full, rejecting task")
                    return None

                # Add to queue with priority
                self._task_queue.put((task.priority, time.time(), task))
                self._stats["total_tasks"] += 1
                self._stats["queued_tasks"] += 1

                logger.info(
                    f"[ASYNC] Task {task.task_id} submitted (priority: {task.priority})",
                )
                return task.task_id

        except Exception as e:
            logger.exception(f"[ASYNC] Error submitting task: {e}")
            return None

    def schedule_task(self, task: AsyncTask, delay_seconds: int = 0) -> str | None:
        """Schedule a task for future execution."""
        try:
            with self._lock:
                task.scheduled_at = datetime.now() + timedelta(seconds=delay_seconds)
                self._scheduled_tasks.append(task)

                logger.info(
                    f"[ASYNC] Task {task.task_id} scheduled for {task.scheduled_at}",
                )
                return task.task_id

        except Exception as e:
            logger.exception(f"[ASYNC] Error scheduling task: {e}")
            return None

    def _scheduler_worker(self) -> None:
        """Process scheduled tasks."""
        while self._running:
            try:
                current_time = datetime.now()

                with self._lock:
                    # Find tasks ready for execution
                    ready_tasks = []
                    remaining_tasks = []

                    for task in self._scheduled_tasks:
                        if (
                            task.scheduled_at is not None
                            and task.scheduled_at <= current_time
                        ):
                            ready_tasks.append(task)
                        else:
                            remaining_tasks.append(task)

                    self._scheduled_tasks = remaining_tasks

                # Submit ready tasks
                for task in ready_tasks:
                    self.submit_task(task)

                time.sleep(1)  # Check every second

            except Exception as e:
                logger.exception(f"[ASYNC] Scheduler error: {e}")

    def _processor_worker(self) -> None:
        """Process tasks from queue."""
        while self._running:
            try:
                # Get batch of tasks
                tasks = []
                for _ in range(min(self.batch_size, self._task_queue.qsize())):
                    try:
                        _, _, task = self._task_queue.get_nowait()
                        tasks.append(task)

                        with self._lock:
                            self._stats["queued_tasks"] -= 1
                            self._stats["processing_tasks"] += 1

                    except queue.Empty:
                        break

                # Process tasks
                if tasks:
                    futures = []
                    for task in tasks:
                        future = self._executor.submit(self._execute_task, task)
                        futures.append((task, future))

                    # Wait for completion
                    for task, future in futures:
                        try:
                            result = future.result(timeout=60)
                            self._handle_task_completion(task, result, None)
                        except Exception as e:
                            self._handle_task_completion(task, None, e)

                time.sleep(0.1)  # Small delay to prevent CPU spinning

            except Exception as e:
                logger.exception(f"[ASYNC] Processor error: {e}")

    def _execute_task(self, task: AsyncTask) -> Any:
        """Execute a single task."""
        start_time = time.time()

        try:
            result = task.function(*task.args, **task.kwargs)

            # Update processing time
            processing_time = time.time() - start_time
            with self._lock:
                total = self._stats["completed_tasks"] + self._stats["failed_tasks"]
                if total > 0:
                    self._stats["avg_processing_time"] = (
                        self._stats["avg_processing_time"] * total + processing_time
                    ) / (total + 1)
                else:
                    self._stats["avg_processing_time"] = processing_time

            return result

        except Exception as e:
            logger.exception(f"[ASYNC] Task {task.task_id} execution failed: {e}")
            raise

    def _handle_task_completion(
        self,
        task: AsyncTask,
        result: Any,
        error: Exception | None,
    ) -> None:
        """Handle task completion."""
        with self._lock:
            self._stats["processing_tasks"] -= 1

            if error:
                task.retry_count += 1

                if task.retry_count <= task.max_retries:
                    # Retry task
                    logger.warning(
                        f"[ASYNC] Retrying task {task.task_id} "
                        f"(attempt {task.retry_count}/{task.max_retries})",
                    )
                    self.submit_task(task)
                else:
                    # Mark as failed
                    self._stats["failed_tasks"] += 1
                    self._failed_tasks.append((task, error))
                    logger.error(
                        f"[ASYNC] Task {task.task_id} failed permanently: {error}",
                    )
            else:
                # Mark as completed
                self._stats["completed_tasks"] += 1
                self._completed_tasks.append((task, result))
                logger.info(f"[ASYNC] Task {task.task_id} completed successfully")

    def get_stats(self) -> dict[str, Any]:
        """Get task processing statistics."""
        with self._lock:
            self._stats["queued_tasks"] = self._task_queue.qsize()
            return self._stats.copy()

    from collections.abc import Sequence

    def get_failed_tasks(self) -> Sequence[tuple[object, Exception]]:
        """Get list[Any] of failed tasks."""
        with self._lock:
            return self._failed_tasks.copy()

    def shutdown(self) -> None:
        """Shutdown the task processor."""
        self._running = False
        self._executor.shutdown(wait=True)
        logger.info("[ASYNC] Task processor shutdown")


class AsyncDatabaseManager:
    """Async database operations manager."""

    def __init__(self, database_path: str = "./data/klerno.db") -> None:
        self.database_path = database_path
        self._pool: DatabaseConnectionPool = DatabaseConnectionPool(database_path)
        self._task_processor: AsyncTaskProcessor = AsyncTaskProcessor()

        logger.info("[ASYNC-DB] Async database manager initialized")

    async def execute_query(self, query: str, params: tuple[Any, ...] = ()) -> Any:
        """Execute async database query."""
        loop = asyncio.get_event_loop()

        def _execute() -> Any:
            conn = self._pool.get_connection()
            if not conn:
                msg = "No database connection available"
                raise Exception(msg)

            try:
                cursor = conn.execute(query, params)
                if query.strip().upper().startswith("SELECT"):
                    return [dict(row) for row in cursor.fetchall()]
                conn.commit()
                return {"affected_rows": cursor.rowcount}
            finally:
                self._pool.return_connection(conn)

        return await loop.run_in_executor(None, _execute)

    async def execute_transaction(self, queries: list[tuple[Any, ...]]) -> bool:
        """Execute multiple queries in a transaction."""
        loop = asyncio.get_event_loop()

        def _execute() -> bool:
            conn = self._pool.get_connection()
            if not conn:
                msg = "No database connection available"
                raise Exception(msg)

            try:
                conn.execute("BEGIN")

                for query, params in queries:
                    conn.execute(query, params or ())

                conn.commit()
                return True

            except Exception:
                conn.rollback()
                raise
            finally:
                self._pool.return_connection(conn)

        return await loop.run_in_executor(None, _execute)

    def submit_background_task(
        self,
        task_func: Callable,
        *args,
        **kwargs,
    ) -> str | None:
        """Submit a background database task."""
        task = AsyncTask(
            task_id=f"db_task_{int(time.time() * 1000)}",
            function=task_func,
            args=args,
            kwargs=kwargs,
            priority=3,
        )

        return self._task_processor.submit_task(task)

    def get_database_stats(self) -> dict[str, Any]:
        """Get comprehensive database statistics."""
        pool_stats = self._pool.get_stats()
        task_stats = self._task_processor.get_stats()

        return {
            "connection_pool": {
                "total_connections": pool_stats.total_connections,
                "active_connections": pool_stats.active_connections,
                "idle_connections": pool_stats.idle_connections,
                "failed_connections": pool_stats.failed_connections,
                "total_queries": pool_stats.total_queries,
                "avg_query_time": pool_stats.avg_query_time,
                "peak_connections": pool_stats.peak_connections,
            },
            "async_tasks": task_stats,
            "uptime_seconds": (datetime.now() - pool_stats.created_at).total_seconds(),
        }

    # Compatibility shim: older callers expect `get_performance_stats`
    def get_performance_stats(self) -> dict[str, Any]:
        """Backward-compatible alias for get_database_stats."""
        return self.get_database_stats()

    def shutdown(self) -> None:
        """Shutdown the database manager."""
        self._task_processor.shutdown()
        self._pool.close_all()
        logger.info("[ASYNC-DB] Database manager shutdown")

    # Make an awaitable shutdown helper for callers that await shutdown()
    async def shutdown_async(self) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.shutdown)


# Global instances
database_manager: AsyncDatabaseManager | None = None


def get_database_manager() -> AsyncDatabaseManager:
    """Get global database manager instance."""
    global database_manager

    if database_manager is None:
        database_manager = AsyncDatabaseManager()

    return database_manager


def initialize_async_database() -> "AsyncDatabaseManager | None":
    """Initialize async database systems."""
    try:
        manager = get_database_manager()
        logger.info("[ASYNC-DB] Enterprise async database systems initialized")
        return manager
    except Exception as e:
        logger.exception(f"[ASYNC-DB] Failed to initialize: {e}")
        return None


if __name__ == "__main__":
    # Test the async database system
    async def test_async_database() -> None:
        manager = get_database_manager()

        # Test query
        await manager.execute_query("SELECT COUNT(*) as count FROM users")

        # Test transaction
        await manager.execute_transaction(
            [
                ("INSERT OR IGNORE INTO test_table (name) VALUES (?)", ("test",)),
                ("UPDATE test_table SET name = ? WHERE name = ?", ("updated", "test")),
            ],
        )

        # Get stats
        manager.get_database_stats()

        manager.shutdown()

    asyncio.run(test_async_database())
