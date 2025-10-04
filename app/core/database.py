"""Klerno Labs - Centralized Database Connection Manager
Fixes ResourceWarning: unclosed database connections by providing proper connection management.
"""

import contextlib
import logging
import sqlite3
import threading
from collections.abc import Generator
from pathlib import Path
from typing import Any

from app._typing_shims import ISyncConnection

logger = logging.getLogger(__name__)


class DatabaseConnectionManager:
    """Centralized SQLite connection manager with proper resource cleanup.
    Ensures all database connections are properly closed to prevent ResourceWarnings.
    """

    def __init__(self, db_path: str | None = None) -> None:
        if db_path is None:
            # Default to Klerno database path
            db_path = str(Path(__file__).parent.parent / "data" / "klerno.db")
        # Normalize to absolute resolved path string for sqlite
        self.db_path = str(Path(db_path).resolve())
        self._local = threading.local()

    @contextlib.contextmanager
    def get_connection(
        self,
        timeout: float = 30.0,
    ) -> Generator[ISyncConnection, None, None]:
        """Get a properly managed database connection that will be automatically closed.

        Args:
            timeout: Connection timeout in seconds

        Yields:
            ISyncConnection: Database connection with proper cleanup

        """
        conn: ISyncConnection | None = None
        try:
            # Create the raw sqlite3 connection and initialize it, then cast
            from typing import cast

            _raw_conn = sqlite3.connect(self.db_path, timeout=timeout)
            _raw_conn.row_factory = sqlite3.Row
            # Cast runtime sqlite3.Connection to ISyncConnection protocol for typing
            conn = cast("ISyncConnection", _raw_conn)
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            conn.execute("PRAGMA temp_store=MEMORY")
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                try:
                    conn.close()
                except Exception as e:
                    logger.warning(f"Error closing database connection: {e}")

    def execute_query(
        self,
        query: str,
        params: tuple[Any, ...] = (),
        fetch_one: bool = False,
        fetch_all: bool = True,
    ) -> Any:
        """Execute a query with proper connection management.

        Args:
            query: SQL query to execute
            params: Query parameters
            fetch_one: Return only first result
            fetch_all: Return all results

        Returns:
            Query results or None

        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)

            if query.strip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
                conn.commit()
                return cursor.rowcount
            if fetch_one:
                return cursor.fetchone()
            if fetch_all:
                return cursor.fetchall()
            return None

    def execute_transaction(self, queries: list[Any]) -> bool:
        """Execute multiple queries in a transaction with proper cleanup.

        Args:
            queries: List of (query, params) tuples

        Returns:
            bool: True if transaction succeeded

        """
        with self.get_connection() as conn:
            try:
                cursor = conn.cursor()
                for query, params in queries:
                    cursor.execute(query, params)
                conn.commit()
                return True
            except Exception as e:
                conn.rollback()
                logger.error(f"Transaction failed: {e}")
                return False


# Global database manager instance
_db_manager = None
_db_manager_lock = threading.Lock()


def get_db_manager(db_path: str | None = None) -> DatabaseConnectionManager:
    """Get the global database manager instance (singleton pattern).

    Args:
        db_path: Optional database path override

    Returns:
        DatabaseConnectionManager: Global database manager

    """
    global _db_manager

    if _db_manager is None:
        with _db_manager_lock:
            if _db_manager is None:
                _db_manager = DatabaseConnectionManager(db_path)

    return _db_manager


# Convenience function for backward compatibility
def get_db_connection(timeout: float = 30.0) -> Any:
    """DEPRECATED: Use get_db_manager().get_connection() instead.
    This function is kept for backward compatibility but will be removed.
    """
    import warnings

    warnings.warn(
        "get_db_connection() is deprecated. Use get_db_manager().get_connection() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return get_db_manager().get_connection(timeout)


# Context manager for legacy code migration
@contextlib.contextmanager
def safe_db_connection(db_path: str | None = None, timeout: float = 30.0) -> Any:
    """Safe database connection context manager for fixing legacy code.

    Args:
        db_path: Optional database path
        timeout: Connection timeout

    Yields:
        ISyncConnection: Properly managed connection

    """
    manager = get_db_manager(db_path)
    with manager.get_connection(timeout) as conn:
        yield conn
