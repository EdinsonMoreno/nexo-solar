"""Repository for irradiance measurement data access.

Provides high-level data access methods for irradiance measurements,
abstracting the underlying database operations.
"""

import re
from typing import Any, Dict, List, Optional

from modbuspython.exceptions import DatabaseError
from modbuspython.data_access.logging_service import LoggingService
from .base_repository import BaseRepository

logger = LoggingService()


class IrradianceRepository(BaseRepository):
    """Repository for irradiance measurement data access.

    Provides high-level data access methods for irradiance measurements,
    abstracting the underlying database operations.

    Requirements validated: 13.1, 13.2
    """

    def create_table(self, table_name: str) -> None:
        """Create irradiance measurements table if it doesn't exist.

        Args:
            table_name: Name of table to create

        Raises:
            DatabaseError: If table creation fails or name is invalid
        """
        if not self._validate_table_name(table_name):
            error_msg = f"Invalid table name: {table_name}"
            logger.error(error_msg, table_name=table_name)
            raise DatabaseError(error_msg, details={"table_name": table_name, "error_type": "validation"})

        query = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                hora TEXT NOT NULL,
                irradiancia REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """

        try:
            logger.info(f"Creating table if not exists: {table_name}")
            self.execute_command(query)
            logger.info(f"Table {table_name} created or already exists")
        except DatabaseError:
            raise

    def insert_measurement(self, table_name: str, fecha: str, hora: str, irradiancia: float) -> None:
        """Insert new irradiance measurement.

        Args:
            table_name: Name of table to insert into
            fecha: Date in YYYY-MM-DD format
            hora: Time in HH:MM:SS format
            irradiancia: Irradiance value in W/m²

        Raises:
            DatabaseError: If insertion fails
        """
        query = f"""
            INSERT INTO {table_name} (fecha, hora, irradiancia)
            VALUES (?, ?, ?)
        """  # nosec B608

        try:
            logger.debug(
                f"Inserting measurement into {table_name}",
                table=table_name,
                fecha=fecha,
                hora=hora,
                irradiancia=irradiancia,
            )
            self.execute_command(query, (fecha, hora, irradiancia))
            logger.debug(f"Measurement inserted successfully into {table_name}")
        except DatabaseError:
            raise

    def get_tables(self) -> List[str]:
        """Get list of existing table names in the database.

        Returns:
            List of table names
        """
        query = """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """

        try:
            logger.debug("Fetching list of tables from database")
            rows = self.execute_query(query)
            tables = [row[0] for row in rows] if rows else []
            logger.debug(f"Found {len(tables)} tables in database")
            return tables
        except DatabaseError:
            logger.error("Failed to fetch table list", exc_info=True)
            return []

    def get_statistics(self, table_name: str) -> Dict[str, Any]:
        """Get statistics for an irradiance table.

        Args:
            table_name: Name of table to analyze

        Returns:
            Dictionary with statistics (count, min, max, avg, etc.)
        """
        query = f"""
            SELECT
                COUNT(*) as count,
                MIN(irradiancia) as min_irradiancia,
                MAX(irradiancia) as max_irradiancia,
                AVG(irradiancia) as avg_irradiancia,
                MIN(fecha || ' ' || hora) as first_datetime,
                MAX(fecha || ' ' || hora) as last_datetime
            FROM {table_name}
        """  # nosec B608

        try:
            logger.debug(f"Fetching statistics for table: {table_name}")
            row = self.execute_query(query, fetch_one=True)

            if row and row[0] > 0:
                stats = {
                    "count": row[0],
                    "min_irradiancia": row[1],
                    "max_irradiancia": row[2],
                    "avg_irradiancia": row[3],
                    "first_datetime": row[4],
                    "last_datetime": row[5],
                }
                logger.debug(f"Statistics retrieved for {table_name}: {row[0]} records")
                return stats
            else:
                logger.debug(f"No records found in table {table_name}")
                return self._empty_statistics()

        except DatabaseError:
            logger.error(f"Failed to fetch statistics for {table_name}", exc_info=True)
            return self._empty_statistics()

    def get_records(
        self,
        table_name: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        raise_on_error: bool = False,
    ) -> List[Dict[str, Any]]:
        """Return measurement rows ordered by date/time, optionally filtered by date range.

        Args:
            table_name: Table to read from.
            date_from: Inclusive lower bound on ``fecha`` (YYYY-MM-DD), optional.
            date_to: Inclusive upper bound on ``fecha`` (YYYY-MM-DD), optional.
            raise_on_error: When True, propagate failures instead of returning an
                empty list. Callers that must tell "query failed" apart from
                "table is empty" need this; swallowing the error collapses both
                into the same result. Defaults to False for backwards
                compatibility with existing callers.

        Returns:
            List of dicts ``{id, fecha, hora, irradiancia}`` (empty on error/invalid
            name unless ``raise_on_error`` is set).

        Raises:
            DatabaseError: Only when ``raise_on_error`` is True.
            ValueError: Invalid table name, only when ``raise_on_error`` is True.
        """
        if not self._validate_table_name(table_name):
            logger.error(f"Invalid table name: {table_name}")
            if raise_on_error:
                raise ValueError(f"Nombre de tabla inválido: {table_name}")
            return []

        query = f"SELECT id, fecha, hora, irradiancia FROM {table_name}"  # nosec B608
        clauses: List[str] = []
        params: List[Any] = []
        if date_from:
            clauses.append("fecha >= ?")
            params.append(date_from)
        if date_to:
            clauses.append("fecha <= ?")
            params.append(date_to)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY fecha, hora"

        try:
            rows = self.execute_query(query, tuple(params))
            return [{"id": r[0], "fecha": r[1], "hora": r[2], "irradiancia": r[3]} for r in (rows or [])]
        except DatabaseError:
            logger.error(f"Failed to fetch records from {table_name}", exc_info=True)
            if raise_on_error:
                raise
            return []

    @staticmethod
    def _validate_table_name(name: str) -> bool:
        """Validate table name against SQLite rules.

        Args:
            name: Table name to validate

        Returns:
            True if valid, False otherwise
        """
        if not name or len(name) == 0:
            return False

        if name[0].isdigit():
            return False

        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
            return False

        reserved_words = {
            "table",
            "index",
            "view",
            "trigger",
            "select",
            "insert",
            "update",
            "delete",
            "create",
            "drop",
            "alter",
            "where",
            "order",
            "group",
            "having",
            "union",
            "join",
            "from",
        }

        if name.lower() in reserved_words:
            return False

        return True

    @staticmethod
    def _empty_statistics() -> Dict[str, Any]:
        """Return empty statistics dictionary.

        Returns:
            Dictionary with None values
        """
        return {
            "count": 0,
            "min_irradiancia": None,
            "max_irradiancia": None,
            "avg_irradiancia": None,
            "first_datetime": None,
            "last_datetime": None,
        }
