"""Database manager with connection pooling and context manager support.

Provides centralized database access with automatic connection management,
transaction handling, and resource cleanup. Uses connection pooling for
improved performance.

Requirements validated: 10.1, 10.6, 17.4
"""

import sqlite3
import os
from typing import Dict, Generator
from contextlib import contextmanager
from threading import Lock

from modbuspython.exceptions import DatabaseError
from modbuspython.data_access.logging_service import LoggingService
from modbuspython.data_access.connection_pool import ConnectionPool

logger = LoggingService()


class DatabaseManager:
    """Database manager with connection pooling and context manager support.

    Provides centralized database access with automatic connection management,
    transaction handling, and resource cleanup. Uses connection pooling for
    improved performance.

    Requirements validated: 10.1, 10.6, 17.4
    """

    _pools: Dict[str, ConnectionPool] = {}
    _pools_lock = Lock()

    @classmethod
    def get_pool(cls, db_path: str, pool_size: int = 5) -> ConnectionPool:
        """Get or create connection pool for database.

        Args:
            db_path: Path to database file
            pool_size: Maximum connections in pool

        Returns:
            ConnectionPool: Connection pool for database
        """
        with cls._pools_lock:
            if db_path not in cls._pools:
                cls._pools[db_path] = ConnectionPool(db_path, pool_size)
            return cls._pools[db_path]

    @classmethod
    def close_all_pools(cls) -> None:
        """Close all connection pools.

        Should be called when shutting down the application.
        Requirements validated: 10.1
        """
        with cls._pools_lock:
            for db_path, pool in cls._pools.items():
                logger.info(f"Closing pool for {db_path}")
                pool.close_all()
            cls._pools.clear()

    @staticmethod
    def _rollback_connection(conn: sqlite3.Connection, reason: str) -> None:
        """Attempt rollback on a connection, logging any errors.

        Args:
            conn: Database connection to rollback
            reason: Description of why rollback is happening
        """
        try:
            conn.rollback()
            logger.warning(f"Transaction rolled back due to {reason}")
        except sqlite3.Error as rollback_error:
            logger.error("Failed to rollback transaction", exc_info=True, error=str(rollback_error))

    @staticmethod
    def _release_connection(
        conn: sqlite3.Connection,
        db_path: str,
        use_pool: bool,
        pool: ConnectionPool | None,
    ) -> None:
        """Return connection to pool or close it directly.

        Args:
            conn: Connection to release
            db_path: Database path (for logging)
            use_pool: Whether pooling is enabled
            pool: Pool instance if pooling is enabled
        """
        if use_pool and pool:
            pool.return_connection(conn)
        else:
            try:
                conn.close()
                logger.debug(f"Connection to {db_path} closed successfully")
            except sqlite3.Error as e:
                logger.error(f"Error closing connection to {db_path}", exc_info=True, error=str(e))

    @staticmethod
    @contextmanager
    def get_connection(
        db_path: str,
        auto_commit: bool = True,
        use_pool: bool = True,
    ) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for database connections with automatic resource cleanup.

        Provides safe database connection handling with automatic commit on success
        and rollback on error. Always closes/returns the connection when exiting.

        Args:
            db_path: Path to SQLite database file
            auto_commit: If True, automatically commit on success and rollback on error
            use_pool: If True, use connection pooling

        Yields:
            sqlite3.Connection: Active database connection

        Raises:
            DatabaseError: If connection fails or other database errors occur

        Requirements validated: 10.1, 10.6, 17.4
        """
        conn = None
        pool = None

        try:
            if use_pool:
                pool = DatabaseManager.get_pool(db_path)
                conn = pool.get_connection()
            else:
                conn = DatabaseManager._create_direct_connection(db_path)

            logger.debug(f"Acquired connection to {db_path} (pooled: {use_pool})")
            yield conn

            if auto_commit:
                conn.commit()
                logger.debug(f"Transaction committed successfully for {db_path}")

        except sqlite3.Error as e:
            if conn and auto_commit:
                DatabaseManager._rollback_connection(conn, str(e))
            if isinstance(e, DatabaseError):
                raise
            error_msg = f"Database operation failed: {str(e)}"
            logger.error(error_msg, exc_info=True, db_path=db_path, error=str(e))
            raise DatabaseError(error_msg, details={"db_path": db_path, "original_error": str(e)})

        except Exception as e:
            if conn and auto_commit:
                DatabaseManager._rollback_connection(conn, f"non-database error: {str(e)}")
            raise

        finally:
            if conn:
                DatabaseManager._release_connection(conn, db_path, use_pool, pool)

    @staticmethod
    def _create_direct_connection(db_path: str) -> sqlite3.Connection:
        """Create a direct database connection without pooling.

        Args:
            db_path: Path to database file

        Returns:
            sqlite3.Connection: Database connection

        Raises:
            DatabaseError: If connection fails
        """
        try:
            directory = os.path.dirname(db_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)

            conn = sqlite3.connect(db_path)
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("SELECT 1")

            logger.debug(f"Created direct connection to {db_path}")
            return conn

        except sqlite3.Error as e:
            error_msg = f"Failed to connect to database {db_path}"
            logger.error(error_msg, exc_info=True, db_path=db_path, error=str(e))
            raise DatabaseError(error_msg, details={"db_path": db_path, "original_error": str(e)})
        except OSError as e:
            error_msg = f"Permission or access error for database file {db_path}"
            logger.error(error_msg, exc_info=True, db_path=db_path, error=str(e))
            raise DatabaseError(
                error_msg,
                details={"db_path": db_path, "original_error": str(e), "error_type": "permission"},
            )


# Backward-compatibility re-exports
from modbuspython.data_access.connection_pool import ConnectionPool  # noqa: E402, F401
from modbuspython.data_access.repositories import (  # noqa: E402, F401
    BaseRepository,
    IrradianceRepository,
    SchemaVersionRepository,
)
