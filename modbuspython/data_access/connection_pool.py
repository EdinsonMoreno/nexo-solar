"""Connection pool for SQLite database connections.

Provides thread-safe connection pooling to improve performance
and reduce connection overhead.
"""

import sqlite3
import os
from queue import Queue, Empty
from threading import Lock

from modbuspython.exceptions import DatabaseError
from modbuspython.data_access.logging_service import LoggingService

logger = LoggingService()


class ConnectionPool:
    """Thread-safe connection pool for SQLite database connections.

    Manages a pool of reusable database connections to improve performance
    and reduce connection overhead. Implements connection lifecycle management
    with automatic cleanup.

    Requirements validated: 17.4
    """

    def __init__(self, db_path: str, pool_size: int = 5, timeout: float = 30.0) -> None:
        """Initialize connection pool.

        Args:
            db_path: Path to SQLite database file
            pool_size: Maximum number of connections in pool
            timeout: Maximum time to wait for available connection (seconds)
        """
        self.db_path = db_path
        self.pool_size = pool_size
        self.timeout = timeout
        self._pool: Queue[sqlite3.Connection] = Queue(maxsize=pool_size)
        self._lock = Lock()
        self._created_connections = 0
        self._closed = False

        logger.info(f"Initialized connection pool for {db_path}", pool_size=pool_size, timeout=timeout)

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection.

        Returns:
            sqlite3.Connection: New database connection

        Raises:
            DatabaseError: If connection creation fails
        """
        try:
            directory = os.path.dirname(self.db_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)

            conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=self.timeout,
            )
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("SELECT 1")

            logger.debug(f"Created new connection to {self.db_path}")
            return conn

        except sqlite3.Error as e:
            error_msg = f"Failed to create connection to {self.db_path}"
            logger.error(error_msg, exc_info=True, db_path=self.db_path, error=str(e))
            raise DatabaseError(error_msg, details={"db_path": self.db_path, "original_error": str(e)})

    def get_connection(self) -> sqlite3.Connection:
        """Get a connection from the pool.

        Returns an existing connection from the pool if available,
        otherwise creates a new one if pool limit not reached.

        Returns:
            sqlite3.Connection: Database connection

        Raises:
            DatabaseError: If pool is closed or timeout exceeded
        """
        if self._closed:
            raise DatabaseError("Connection pool is closed")

        try:
            conn = self._pool.get(block=True, timeout=self.timeout)
            logger.debug("Retrieved connection from pool")
            return conn

        except Empty:
            with self._lock:
                if self._created_connections < self.pool_size:
                    conn = self._create_connection()
                    self._created_connections += 1
                    logger.debug(f"Created new connection ({self._created_connections}/{self.pool_size})")
                    return conn
                else:
                    error_msg = f"Connection pool exhausted (timeout: {self.timeout}s)"
                    logger.error(error_msg, pool_size=self.pool_size)
                    raise DatabaseError(error_msg, details={"pool_size": self.pool_size, "timeout": self.timeout})

    def return_connection(self, conn: sqlite3.Connection) -> None:
        """Return a connection to the pool.

        Args:
            conn: Connection to return to pool
        """
        if self._closed:
            try:
                conn.close()
                logger.debug("Closed connection (pool is closed)")
            except sqlite3.Error as e:
                logger.error("Error closing connection", exc_info=True, error=str(e))
            return

        try:
            conn.rollback()
            self._pool.put(conn, block=False)
            logger.debug("Returned connection to pool")
        except Exception as e:
            logger.warning(f"Failed to return connection to pool: {e}")
            try:
                conn.close()
                with self._lock:
                    self._created_connections -= 1
            except sqlite3.Error as close_error:
                logger.error("Error closing connection", exc_info=True, error=str(close_error))

    def close_all(self) -> None:
        """Close all connections in the pool.

        Should be called when shutting down the application.
        Requirements validated: 10.1
        """
        self._closed = True
        logger.info("Closing all connections in pool")

        closed_count = 0
        while not self._pool.empty():
            try:
                conn = self._pool.get(block=False)
                conn.close()
                closed_count += 1
            except Empty:
                break
            except sqlite3.Error as e:
                logger.error("Error closing pooled connection", exc_info=True, error=str(e))

        logger.info(f"Closed {closed_count} connections from pool")
