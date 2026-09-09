"""

Unit tests for DatabaseManager context manager functionality.


Tests verify that:

- Connections are properly opened and closed

- Transactions are committed on success

- Transactions are rolled back on error

- Resources are cleaned up in all scenarios
"""

import pytest

import sqlite3

import tempfile
import os

from pathlib import Path


from modbuspython.backend.sqlite_manager import DatabaseManager, crear_tabla, insert_record
from modbuspython.exceptions import DatabaseError


class TestDatabaseContextManager:
    """Test suite for DatabaseManager context manager."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database file path."""

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".db") as f:

            db_path = f.name

        yield db_path

        # Cleanup

        if os.path.exists(db_path):

            os.unlink(db_path)

    def test_context_manager_opens_and_closes_connection(self, temp_db_path):
        """Test that context manager properly opens and closes connections."""

        # Use context manager

        with DatabaseManager.get_connection(temp_db_path) as conn:

            assert conn is not None

            assert isinstance(conn, sqlite3.Connection)

            # Verify connection is active

            cursor = conn.cursor()

            cursor.execute("SELECT 1")

            result = cursor.fetchone()

            assert result[0] == 1

        # After exiting context, connection should be closed

        # Attempting to use it should raise an error

        with pytest.raises(sqlite3.ProgrammingError, match="Cannot operate on a closed database"):

            conn.execute("SELECT 1")

    def test_context_manager_commits_on_success(self, temp_db_path):
        """Test that successful operations are automatically committed."""

        table_name = "test_table"

        # Create table and insert data in context

        with DatabaseManager.get_connection(temp_db_path) as conn:

            crear_tabla(conn, table_name)
            insert_record(conn, table_name, "2024-01-01", "12:00:00", 850.5)

        # Verify data was committed by opening new connection

        with DatabaseManager.get_connection(temp_db_path) as conn:

            cursor = conn.cursor()

            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")

            count = cursor.fetchone()[0]

            assert count == 1

    def test_context_manager_rollback_on_error(self, temp_db_path):
        """Test that transactions are rolled back on error."""

        table_name = "test_table"

        # First, create table successfully

        with DatabaseManager.get_connection(temp_db_path) as conn:

            crear_tabla(conn, table_name)

        # Now try to execute operations but cause an error before commit

        try:

            with DatabaseManager.get_connection(temp_db_path) as conn:

                cursor = conn.cursor()

                # Insert directly without using insertar_registro (which commits internally)

                cursor.execute(
                    f"INSERT INTO {table_name} (fecha, hora, irradiancia) VALUES (?, ?, ?)",
                    ("2024-01-01", "12:00:00", 850.5),
                )

                # Force an error by executing invalid SQL before commit

                conn.execute("INVALID SQL STATEMENT")

        except (sqlite3.Error, DatabaseError):

            pass  # Expected error

        # Verify that the insert was rolled back

        with DatabaseManager.get_connection(temp_db_path) as conn:

            cursor = conn.cursor()

            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")

            count = cursor.fetchone()[0]

            assert count == 0, "Insert should have been rolled back"

    def test_context_manager_with_auto_commit_false(self, temp_db_path):
        """Test context manager with auto_commit=False."""

        table_name = "test_table"

        # Create table with auto_commit disabled

        with DatabaseManager.get_connection(temp_db_path, auto_commit=False) as conn:

            crear_tabla(conn, table_name)

            # Manual commit required
            conn.commit()

        # Verify table exists

        with DatabaseManager.get_connection(temp_db_path) as conn:

            cursor = conn.cursor()

            cursor.execute(
                """

                SELECT name FROM sqlite_master

                WHERE type='table' AND name=?

            """,
                (table_name,),
            )

            result = cursor.fetchone()

            assert result is not None

    def test_context_manager_closes_on_exception(self, temp_db_path):
        """Test that connection is closed even when exception occurs."""

        conn_ref = None

        try:

            with DatabaseManager.get_connection(temp_db_path) as conn:

                conn_ref = conn

                # Raise an exception

                raise ValueError("Test exception")

        except ValueError:

            pass  # Expected

        # Connection should still be closed

        assert conn_ref is not None

        with pytest.raises(sqlite3.ProgrammingError, match="Cannot operate on a closed database"):

            conn_ref.execute("SELECT 1")

    def test_context_manager_with_nonexistent_directory(self):
        """Test context manager creates directory if it doesn't exist."""

        temp_dir = tempfile.mkdtemp()

        db_path = os.path.join(temp_dir, "subdir", "test.db")

        try:

            with DatabaseManager.get_connection(db_path) as conn:

                assert conn is not None

                cursor = conn.cursor()

                cursor.execute("SELECT 1")

            # Verify database file was created

            assert os.path.exists(db_path)

        finally:

            # Cleanup - add small delay for Windows file locking
            import time

            time.sleep(0.1)

            try:

                if os.path.exists(db_path):

                    os.unlink(db_path)

                if os.path.exists(os.path.dirname(db_path)):
                    os.rmdir(os.path.dirname(db_path))

                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)

            except (PermissionError, OSError):

                # On Windows, file might still be locked - ignore cleanup errors in tests
                pass

    def test_multiple_operations_in_single_context(self, temp_db_path):
        """Test multiple database operations within a single context."""

        table_name = "test_table"

        with DatabaseManager.get_connection(temp_db_path) as conn:

            # Create table

            crear_tabla(conn, table_name)

            # Insert multiple records
            insert_record(conn, table_name, "2024-01-01", "12:00:00", 850.5)
            insert_record(conn, table_name, "2024-01-01", "13:00:00", 920.3)
            insert_record(conn, table_name, "2024-01-01", "14:00:00", 780.1)

        # Verify all records were committed

        with DatabaseManager.get_connection(temp_db_path) as conn:

            cursor = conn.cursor()

            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")

            count = cursor.fetchone()[0]

            assert count == 3

    def test_nested_context_managers(self, temp_db_path):
        """Test that nested context managers work correctly (though not recommended)."""

        table_name = "test_table"

        # Outer context

        with DatabaseManager.get_connection(temp_db_path) as conn1:

            crear_tabla(conn1, table_name)
            insert_record(conn1, table_name, "2024-01-01", "12:00:00", 850.5)

        # Inner context (new connection)

        with DatabaseManager.get_connection(temp_db_path) as conn2:

            cursor = conn2.cursor()

            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")

            count = cursor.fetchone()[0]

            assert count == 1

    def test_context_manager_with_database_error(self, temp_db_path):
        """Test that DatabaseError is properly raised and handled."""

        with pytest.raises(DatabaseError):

            with DatabaseManager.get_connection(temp_db_path) as conn:

                # Try to insert into non-existent table

                conn.execute("INSERT INTO nonexistent_table VALUES (1, 2, 3)")
