"""Repository for database schema version tracking.

Manages schema version information to support database migrations
and ensure compatibility between application and database schema.
"""

import sqlite3
from typing import Any, Dict, Optional

from modbuspython.exceptions import DatabaseError
from modbuspython.data_access.logging_service import LoggingService
from .base_repository import BaseRepository

logger = LoggingService()


class SchemaVersionRepository(BaseRepository):
    """Repository for database schema version tracking.

    Manages schema version information to support database migrations
    and ensure compatibility between application and database schema.

    Requirements validated: 13.1, 13.7
    """

    SCHEMA_VERSION_TABLE = "schema_version"

    def __init__(self, db_path: str, use_pool: bool = True) -> None:
        """Initialize schema version repository.

        Args:
            db_path: Path to database file
            use_pool: Whether to use connection pooling
        """
        super().__init__(db_path, use_pool)
        self._ensure_version_table()

    def _ensure_version_table(self) -> None:
        """Create schema_version table if it doesn't exist.

        The schema_version table tracks the current version of the database
        schema to enable migration management.

        Raises:
            DatabaseError: If table creation fails
        """
        query = f"""
            CREATE TABLE IF NOT EXISTS {self.SCHEMA_VERSION_TABLE} (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                version INTEGER NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        """

        try:
            logger.debug(f"Ensuring {self.SCHEMA_VERSION_TABLE} table exists")
            self.execute_command(query)

            with self.get_connection(auto_commit=False) as conn:
                cursor = conn.cursor()
                cursor.execute(f"SELECT COUNT(*) FROM {self.SCHEMA_VERSION_TABLE}")  # nosec B608
                count = cursor.fetchone()[0]

                if count == 0:
                    cursor.execute(
                        f"""
                        INSERT INTO {self.SCHEMA_VERSION_TABLE}
                        (id, version, description)
                        VALUES (1, 0, 'Initial schema version')
                        """,  # nosec B608
                    )
                    conn.commit()
                    logger.info("Initialized schema version to 0")
                else:
                    logger.debug(f"{self.SCHEMA_VERSION_TABLE} table already initialized")

        except sqlite3.Error as e:
            error_msg = f"Failed to create {self.SCHEMA_VERSION_TABLE} table"
            logger.error(error_msg, exc_info=True, error=str(e))
            raise DatabaseError(error_msg, details={"original_error": str(e)})

    def get_schema_version(self) -> int:
        """Get current schema version from database.

        Returns:
            Current schema version number (0 if not set)

        Raises:
            DatabaseError: If version retrieval fails

        Requirements validated: 13.1, 13.7
        """
        query = f"""
            SELECT version FROM {self.SCHEMA_VERSION_TABLE}
            WHERE id = 1
        """  # nosec B608

        try:
            logger.debug("Retrieving current schema version")
            row = self.execute_query(query, fetch_one=True)

            if row:
                version = int(row[0])
                logger.info(f"Current schema version: {version}")
                return version
            else:
                logger.warning("No schema version found, returning 0")
                return 0

        except DatabaseError as e:
            logger.error("Failed to retrieve schema version", exc_info=True)
            raise DatabaseError("Failed to retrieve schema version", details={"original_error": str(e)})

    def set_schema_version(self, version: int, description: Optional[str] = None) -> None:
        """Set schema version in database.

        Updates the schema version to track applied migrations.

        Args:
            version: New schema version number
            description: Optional description of the version/migration

        Raises:
            DatabaseError: If version update fails
            ValueError: If version is negative

        Requirements validated: 13.1, 13.7
        """
        if version < 0:
            raise ValueError(f"Schema version must be non-negative, got {version}")

        query = f"""
            UPDATE {self.SCHEMA_VERSION_TABLE}
            SET version = ?,
                applied_at = CURRENT_TIMESTAMP,
                description = ?
            WHERE id = 1
        """  # nosec B608

        try:
            logger.info(f"Setting schema version to {version}", version=version, description=description)

            rows_affected = self.execute_command(query, (version, description or f"Schema version {version}"))

            if rows_affected == 0:
                error_msg = "Failed to update schema version (no rows affected)"
                logger.error(error_msg)
                raise DatabaseError(error_msg, details={"version": version})

            logger.info(f"Schema version updated to {version}")

        except DatabaseError:
            raise
        except Exception as e:
            error_msg = f"Failed to set schema version to {version}"
            logger.error(error_msg, exc_info=True, error=str(e))
            raise DatabaseError(error_msg, details={"version": version, "original_error": str(e)})

    def get_version_info(self) -> Optional[Dict[str, Any]]:
        """Get detailed schema version information.

        Returns:
            Dictionary with version, applied_at, and description, or None if not found

        Raises:
            DatabaseError: If query fails
        """
        query = f"""
            SELECT version, applied_at, description
            FROM {self.SCHEMA_VERSION_TABLE}
            WHERE id = 1
        """  # nosec B608

        try:
            logger.debug("Retrieving schema version information")
            row = self.execute_query(query, fetch_one=True)

            if row:
                info = {
                    "version": row[0],
                    "applied_at": row[1],
                    "description": row[2],
                }
                logger.debug(f"Schema version info: {info}")
                return info
            else:
                logger.warning("No schema version information found")
                return None

        except DatabaseError:
            logger.error("Failed to retrieve schema version info", exc_info=True)
            raise
