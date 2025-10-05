import queue
import sqlite3
import threading
from collections.abc import Generator
from contextlib import contextmanager


class DatabaseConnectionPool:
    """Simple database connection pool for SQLite."""

    def __init__(self, database_path: str, pool_size: int = 10) -> None:
        self.database_path = database_path
        self.pool_size = pool_size
        self.pool = queue.Queue(maxsize=pool_size)
        self.lock = threading.Lock()

        # Initialize pool with connections
        for _ in range(pool_size):
            conn = sqlite3.connect(database_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            self.pool.put(conn)

    @contextmanager
    def get_connection(
        self, timeout: float = 30.0,
    ) -> Generator[sqlite3.Connection, None, None]:
        """Get connection from pool with automatic return."""
        conn = None
        try:
            conn = self.pool.get(timeout=timeout)
            yield conn
        finally:
            if conn:
                self.pool.put(conn)

    def close_all(self) -> None:
        """Close all connections in the pool."""
        while not self.pool.empty():
            try:
                conn = self.pool.get_nowait()
                conn.close()
            except queue.Empty:
                break


# Global connection pool
db_pool = None


def initialize_connection_pool(database_path: str = "./data/klerno.db") -> None:
    """Initialize the global connection pool."""
    global db_pool
    db_pool = DatabaseConnectionPool(database_path)


def get_pooled_connection():
    """Get a connection from the pool."""
    if db_pool is None:
        initialize_connection_pool()
    return db_pool.get_connection()


# Usage example:
# with get_pooled_connection() as conn:
#     cursor = conn.cursor()
#     cursor.execute("SELECT * FROM users LIMIT 1")
#     result = cursor.fetchone()
