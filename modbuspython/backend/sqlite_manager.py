"""SQLite database management for Nexo Solar.

DEPRECATED: This module is maintained for backward compatibility only.
New code should use modbuspython.data_access.database_manager instead.

This module provides functions for managing SQLite database connections,
creating tables, and inserting irradiance measurement records. Implements
safe connection handling with context managers and comprehensive error handling.

Requirements validated: 4.4, 7.2, 7.7, 7.8, 10.1, 10.6
"""

import sqlite3
from typing import List, Generator
from contextlib import contextmanager
import warnings

from modbuspython.exceptions import DatabaseError
from modbuspython.data_access.logging_service import LoggingService

# Import new implementation
from modbuspython.data_access.database_manager import (
    DatabaseManager as NewDatabaseManager,
)

# Initialize logging service
logger = LoggingService()

# Issue deprecation warning
warnings.warn(
    "modbuspython.backend.sqlite_manager is deprecated. " "Use modbuspython.data_access.database_manager instead.",
    DeprecationWarning,
    stacklevel=2,
)


class DatabaseManager:
    """Database manager with context manager support for safe connection handling.

    DEPRECATED: Use modbuspython.data_access.database_manager.DatabaseManager instead.

    Provides automatic connection management with commit/rollback on success/failure.
    Use as a context manager to ensure connections are properly closed and
    transactions are handled correctly.

    Requirements validated: 10.1, 10.6

    Example:
        >>> with DatabaseManager.get_connection('data/db.sqlite') as conn:
        ...     cursor = conn.cursor()
        ...     cursor.execute("SELECT * FROM measurements")
        ...     # Automatic commit on success, rollback on exception
    """

    @staticmethod
    @contextmanager
    def get_connection(ruta_db: str, auto_commit: bool = True) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for database connections with automatic resource cleanup.

        DEPRECATED: Use modbuspython.data_access.database_manager.DatabaseManager.get_connection instead.

        Provides safe database connection handling with automatic commit on success
        and rollback on error. Always closes the connection when exiting the context.

        Args:
            ruta_db: Path to SQLite database file
            auto_commit: If True, automatically commit on success and rollback on error

        Yields:
            sqlite3.Connection: Active database connection

        Raises:
            DatabaseError: If connection fails or other database errors occur

        Requirements validated: 10.1, 10.6

        Example:
            >>> with DatabaseManager.get_connection('data/db.sqlite') as conn:
            ...     cursor = conn.cursor()
            ...     cursor.execute("INSERT INTO measurements VALUES (?, ?, ?)", (date, time, value))
            ...     # Automatic commit when exiting context successfully
        """
        # Use new implementation with pooling disabled for backward compatibility
        with NewDatabaseManager.get_connection(ruta_db, auto_commit=auto_commit, use_pool=False) as conn:
            yield conn


def connect_db(ruta_db: str) -> sqlite3.Connection:
    """Connect to SQLite database, creating file if it doesn't exist.

    DEPRECATED: Use modbuspython.data_access.database_manager.DatabaseManager instead.

    Creates the database directory if needed and verifies the connection works.

    Args:
        ruta_db: Path to SQLite database file

    Returns:
        sqlite3.Connection: Active database connection

    Raises:
        DatabaseError: If connection fails due to permissions or other errors

    Requirements validated: 4.4, 10.1
    """
    return NewDatabaseManager._create_direct_connection(ruta_db)


def get_tables(conn: sqlite3.Connection) -> List[str]:
    """Get list of existing table names in the database.

    DEPRECATED: Use IrradianceRepository.get_tables() instead.

    Useful for verifying database structure before creating new tables.
    Excludes SQLite internal tables.

    Args:
        conn: Active database connection

    Returns:
        List[str]: List of table names (empty list if error occurs)

    Requirements validated: 4.4
    """
    try:
        logger.debug("Fetching list of tables from database")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        tablas = [row[0] for row in cursor.fetchall()]
        logger.debug(f"Found {len(tablas)} tables in database")
        return tablas

    except sqlite3.Error as e:
        error_msg = "Failed to fetch table list from database"
        logger.error(error_msg, exc_info=True, error=str(e))
        # Return empty list to allow application to continue
        return []


def crear_tabla(conn: sqlite3.Connection, nombre_tabla: str) -> None:
    """Create table for storing irradiance readings if it doesn't exist.

    DEPRECATED: Use IrradianceRepository.create_table() instead.

    Creates a table with columns: id (autoincrement), fecha (date), hora (time),
    and irradiancia (irradiance value). Validates table name before creation.

    Args:
        conn: Active database connection
        nombre_tabla: Name of table to create

    Raises:
        DatabaseError: If table creation fails or name is invalid

    Requirements validated: 4.4, 7.2, 7.8
    """
    # Validate table name
    if not validate_table_name(nombre_tabla):
        error_msg = f"Invalid table name: {nombre_tabla}"
        logger.error(error_msg, table_name=nombre_tabla)
        raise DatabaseError(error_msg, details={"table_name": nombre_tabla, "error_type": "validation"})

    try:
        logger.info(f"Creating table if not exists: {nombre_tabla}")
        cursor = conn.cursor()
        sql_crear_tabla = f"""
            CREATE TABLE IF NOT EXISTS {nombre_tabla} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                hora TEXT NOT NULL,
                irradiancia REAL NOT NULL
            )
        """
        cursor.execute(sql_crear_tabla)
        conn.commit()
        logger.info(f"Table {nombre_tabla} created or already exists")

    except sqlite3.Error as e:
        error_msg = f"Failed to create table {nombre_tabla}"
        logger.error(error_msg, exc_info=True, table_name=nombre_tabla, error=str(e))
        # Attempt rollback to maintain database consistency
        try:
            conn.rollback()
            logger.debug("Transaction rolled back after table creation failure")
        except sqlite3.Error as rollback_error:
            logger.error("Failed to rollback transaction", exc_info=True, error=str(rollback_error))

        raise DatabaseError(error_msg, details={"table_name": nombre_tabla, "original_error": str(e)})


def _rollback_safe(conn: sqlite3.Connection, context: str) -> None:
    """Attempt a safe rollback, logging any rollback errors.

    Args:
        conn: Active database connection
        context: Description of the operation that failed (for logging)
    """
    try:
        conn.rollback()
        logger.debug(f"Transaction rolled back after {context}")
    except sqlite3.Error as rollback_error:
        logger.error("Failed to rollback transaction", exc_info=True, error=str(rollback_error))


def insert_record(conn: sqlite3.Connection, nombre_tabla: str, fecha: str, hora: str, irradiancia: float) -> None:
    """Insert new irradiance measurement record into specified table.

    DEPRECATED: Use IrradianceRepository.insert_measurement() instead.

    Uses parameterized queries to prevent SQL injection. Automatically commits
    the transaction on success.

    Args:
        conn: Active database connection
        nombre_tabla: Name of table to insert into
        fecha: Date in YYYY-MM-DD format
        hora: Time in HH:MM:SS format
        irradiancia: Irradiance value in W/m²

    Raises:
        DatabaseError: If insertion fails due to constraints or other errors

    Requirements validated: 4.4, 7.7, 7.8
    """
    try:
        logger.debug(
            f"Inserting record into {nombre_tabla}", table=nombre_tabla, fecha=fecha, hora=hora, irradiancia=irradiancia
        )
        cursor = conn.cursor()
        sql_insertar = f"""
            INSERT INTO {nombre_tabla} (fecha, hora, irradiancia)
            VALUES (?, ?, ?)
        """  # nosec B608
        cursor.execute(sql_insertar, (fecha, hora, irradiancia))
        conn.commit()
        logger.debug(f"Record inserted successfully into {nombre_tabla}")

    except sqlite3.IntegrityError as e:
        error_msg = f"Integrity constraint violation when inserting into {nombre_tabla}"
        logger.error(error_msg, exc_info=True, table=nombre_tabla, fecha=fecha, hora=hora, error=str(e))
        _rollback_safe(conn, "integrity error")
        raise DatabaseError(
            error_msg,
            details={
                "table_name": nombre_tabla,
                "fecha": fecha,
                "hora": hora,
                "irradiancia": irradiancia,
                "original_error": str(e),
                "error_type": "integrity",
            },
        )

    except sqlite3.OperationalError as e:
        error_msg = f"Operational error when inserting into {nombre_tabla}"
        logger.error(error_msg, exc_info=True, table=nombre_tabla, error=str(e))
        _rollback_safe(conn, "operational error")
        raise DatabaseError(
            error_msg, details={"table_name": nombre_tabla, "original_error": str(e), "error_type": "operational"}
        )

    except sqlite3.Error as e:
        error_msg = f"Failed to insert record into {nombre_tabla}"
        logger.error(error_msg, exc_info=True, table=nombre_tabla, fecha=fecha, hora=hora, error=str(e))
        _rollback_safe(conn, "insert failure")
        raise DatabaseError(
            error_msg,
            details={
                "table_name": nombre_tabla,
                "fecha": fecha,
                "hora": hora,
                "irradiancia": irradiancia,
                "original_error": str(e),
            },
        )


def validate_table_name(nombre: str) -> bool:
    """Validate that table name complies with SQLite rules.

    DEPRECATED: Use IrradianceRepository._validate_table_name() instead.

    Checks that the name:
    - Is not empty
    - Doesn't start with a digit
    - Contains only letters, numbers, and underscores
    - Is not a SQL reserved keyword

    Args:
        nombre: Table name to validate

    Returns:
        bool: True if valid, False otherwise

    Requirements validated: 7.2, 7.8
    """
    if not nombre or len(nombre) == 0:
        return False
    # No debe empezar con número
    if nombre[0].isdigit():
        return False
    # Solo letras, números y guiones bajos
    import re

    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", nombre):
        return False
    # No debe ser palabra reservada de SQLite
    palabras_reservadas = {
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
    if nombre.lower() in palabras_reservadas:
        return False
    return True


def get_table_statistics(conn: sqlite3.Connection, nombre_tabla: str) -> dict:
    """Get basic statistics for an irradiance table.

    DEPRECATED: Use IrradianceRepository.get_statistics() instead.

    Calculates count, min, max, average irradiance values, and first/last
    datetime entries. Returns empty statistics if table doesn't exist or
    has no records.

    Args:
        conn: Active database connection
        nombre_tabla: Name of table to analyze

    Returns:
        dict: Dictionary with statistics:
            - count: Number of records
            - min_irradiancia: Minimum irradiance value
            - max_irradiancia: Maximum irradiance value
            - avg_irradiancia: Average irradiance value
            - first_datetime: First record datetime
            - last_datetime: Last record datetime
            Returns None values if table is empty or error occurs

    Requirements validated: 4.4
    """
    try:
        logger.debug(f"Fetching statistics for table: {nombre_tabla}")
        cursor = conn.cursor()
        # Count records and irradiance statistics
        sql_stats = f"""
            SELECT
                COUNT(*) as count,
                MIN(irradiancia) as min_irradiancia,
                MAX(irradiancia) as max_irradiancia,
                AVG(irradiancia) as avg_irradiancia,
                MIN(fecha || ' ' || hora) as first_datetime,
                MAX(fecha || ' ' || hora) as last_datetime
            FROM {nombre_tabla}
        """  # nosec B608
        cursor.execute(sql_stats)
        row = cursor.fetchone()

        if row and row[0] > 0:  # If there are records
            stats = {
                "count": row[0],
                "min_irradiancia": row[1],
                "max_irradiancia": row[2],
                "avg_irradiancia": row[3],
                "first_datetime": row[4],
                "last_datetime": row[5],
            }
            logger.debug(f"Statistics retrieved for {nombre_tabla}: {row[0]} records")
            return stats
        else:
            logger.debug(f"No records found in table {nombre_tabla}")
            return {
                "count": 0,
                "min_irradiancia": None,
                "max_irradiancia": None,
                "avg_irradiancia": None,
                "first_datetime": None,
                "last_datetime": None,
            }

    except sqlite3.OperationalError as e:
        error_msg = f"Table {nombre_tabla} does not exist or cannot be accessed"
        logger.error(error_msg, exc_info=True, table=nombre_tabla, error=str(e))
        # Return empty statistics to allow application to continue
        return {
            "count": 0,
            "min_irradiancia": None,
            "max_irradiancia": None,
            "avg_irradiancia": None,
            "first_datetime": None,
            "last_datetime": None,
        }

    except sqlite3.Error as e:
        error_msg = f"Failed to fetch statistics for table {nombre_tabla}"
        logger.error(error_msg, exc_info=True, table=nombre_tabla, error=str(e))
        # Return empty statistics to allow application to continue
        return {
            "count": 0,
            "min_irradiancia": None,
            "max_irradiancia": None,
            "avg_irradiancia": None,
            "first_datetime": None,
            "last_datetime": None,
        }
