"""Base repository class providing common database operations.

Implements the Repository pattern to abstract data access logic.
"""

import sqlite3
from typing import Any, Generator, Optional
from contextlib import contextmanager

from modbuspython.exceptions import DatabaseError
from modbuspython.data_access.logging_service import LoggingService
from modbuspython.data_access.database_manager import DatabaseManager

logger = LoggingService()


class BaseRepository:
    """Base repository class providing common database operations.

    Implements the Repository pattern to abstract data access logic.
    Subclasses should implement specific data access methods.

    Requirements validated: 13.1, 13.2
    """

    def __init__(self, db_path: str, use_pool: bool = True) -> None:
        """Initialize repository.

        Args:
            db_path: Path to database file
            use_pool: Whether to use connection pooling
        """
        self.db_path = db_path
        self.use_pool = use_pool
        logger.debug(f"Initialized repository for {db_path}")

    @contextmanager
    def get_connection(self, auto_commit: bool = True) -> Generator[sqlite3.Connection, None, None]:
        """Get database connection using context manager.

        Args:
            auto_commit: Whether to auto-commit transactions

        Yields:
            sqlite3.Connection: Database connection
        """
        with DatabaseManager.get_connection(self.db_path, auto_commit=auto_commit, use_pool=self.use_pool) as conn:
            yield conn

    def execute_query(self, query: str, params: tuple = (), fetch_one: bool = False) -> Optional[Any]:
        """Execute a query and return results.

        Args:
            query: SQL query to execute
            params: Query parameters
            fetch_one: If True, return single row; otherwise return all rows

        Returns:
            Query results or None

        Raises:
            DatabaseError: If query execution fails
        """
        try:
            with self.get_connection(auto_commit=False) as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)

                if fetch_one:
                    return cursor.fetchone()
                return cursor.fetchall()

        except sqlite3.Error as e:
            error_msg = f"Query execution failed: {query}"
            logger.error(error_msg, exc_info=True, query=query, error=str(e))
            raise DatabaseError(error_msg, details={"query": query, "params": params, "original_error": str(e)})

    def execute_command(self, command: str, params: tuple = ()) -> int:
        """Execute a command (INSERT, UPDATE, DELETE) and return affected rows.

        Args:
            command: SQL command to execute
            params: Command parameters

        Returns:
            Number of affected rows

        Raises:
            DatabaseError: If command execution fails
        """
        try:
            with self.get_connection(auto_commit=True) as conn:
                cursor = conn.cursor()
                cursor.execute(command, params)
                return int(cursor.rowcount)

        except sqlite3.Error as e:
            error_msg = f"Command execution failed: {command}"
            logger.error(error_msg, exc_info=True, command=command, error=str(e))
            raise DatabaseError(error_msg, details={"command": command, "params": params, "original_error": str(e)})
