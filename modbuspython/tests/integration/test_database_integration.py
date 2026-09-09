"""Integration tests with real database operations.

Tests the current data-access layer (``DatabaseManager`` + ``IrradianceRepository``)
against actual temporary SQLite database files, verifying that:

- Connections are established and managed correctly (pooling disabled for isolation)
- The context manager auto-commits on success and rolls back on error
- Tables are created with the real schema
- Data insertion and retrieval work correctly
- Statistics and integrity constraints behave as expected

Schema under test (created by ``IrradianceRepository.create_table``)::

    id          INTEGER PRIMARY KEY AUTOINCREMENT
    fecha       TEXT NOT NULL
    hora        TEXT NOT NULL
    irradiancia REAL NOT NULL
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
"""

import sqlite3

import pytest

from modbuspython.data_access.database_manager import DatabaseManager
from modbuspython.data_access.repositories.irradiance_repository import IrradianceRepository
from modbuspython.exceptions import DatabaseError

# Expected column order produced by IrradianceRepository.create_table
EXPECTED_COLUMNS = ["id", "fecha", "hora", "irradiancia", "created_at"]


@pytest.fixture
def repo(tmp_path):
    """Return an IrradianceRepository backed by an isolated temp DB (no pooling)."""
    db_path = tmp_path / "test_integration.db"
    return IrradianceRepository(str(db_path), use_pool=False)


def _count(db_path: str, table: str) -> int:
    with DatabaseManager.get_connection(db_path, use_pool=False) as conn:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


class TestDatabaseConnection:
    """Test database connection handling via DatabaseManager."""

    def test_connect_to_new_database(self, tmp_path):
        """Opening a connection creates the database file."""
        db_path = tmp_path / "new_database.db"

        with DatabaseManager.get_connection(str(db_path), use_pool=False) as conn:
            assert isinstance(conn, sqlite3.Connection)

        assert db_path.exists()

    def test_connect_to_existing_database(self, tmp_path):
        """Re-opening an existing database works."""
        db_path = tmp_path / "existing_database.db"

        with DatabaseManager.get_connection(str(db_path), use_pool=False):
            pass

        with DatabaseManager.get_connection(str(db_path), use_pool=False) as conn:
            assert isinstance(conn, sqlite3.Connection)

    def test_context_manager_auto_commit(self, repo):
        """The context manager commits the transaction on clean exit."""
        repo.create_table("test_table")

        with DatabaseManager.get_connection(repo.db_path, use_pool=False) as conn:
            conn.execute(
                "INSERT INTO test_table (fecha, hora, irradiancia) VALUES (?, ?, ?)",
                ("2026-06-05", "10:00:00", 750.0),
            )

        # A fresh connection must see the committed row.
        assert _count(repo.db_path, "test_table") == 1

    def test_context_manager_rollback_on_exception(self, repo):
        """The context manager rolls back when the block raises."""
        repo.create_table("test_table")

        with pytest.raises(ValueError):
            with DatabaseManager.get_connection(repo.db_path, use_pool=False) as conn:
                conn.execute(
                    "INSERT INTO test_table (fecha, hora, irradiancia) VALUES (?, ?, ?)",
                    ("2026-06-05", "10:00:00", 750.0),
                )
                raise ValueError("Test exception before commit")

        assert _count(repo.db_path, "test_table") == 0


class TestTableOperations:
    """Test table creation and management."""

    def test_create_table(self, repo):
        """A created table exists and has the expected schema."""
        repo.create_table("measurements")

        assert "measurements" in repo.get_tables()

        with DatabaseManager.get_connection(repo.db_path, use_pool=False) as conn:
            columns = [col[1] for col in conn.execute("PRAGMA table_info(measurements)").fetchall()]

        assert columns == EXPECTED_COLUMNS

    def test_create_table_idempotent(self, repo):
        """Creating the same table twice does not fail or duplicate it."""
        repo.create_table("measurements")
        repo.create_table("measurements")

        assert repo.get_tables().count("measurements") == 1

    def test_list_tables(self, repo):
        """All created tables are listed."""
        for name in ("measurements", "test_table_1", "test_table_2"):
            repo.create_table(name)

        tables = repo.get_tables()

        assert "measurements" in tables
        assert "test_table_1" in tables
        assert "test_table_2" in tables
        assert len(tables) == 3

    def test_validate_table_name(self):
        """Table name validation accepts safe names and rejects unsafe ones."""
        # Valid names
        assert IrradianceRepository._validate_table_name("measurements") is True
        assert IrradianceRepository._validate_table_name("test_table") is True
        assert IrradianceRepository._validate_table_name("table123") is True
        assert IrradianceRepository._validate_table_name("_private_table") is True

        # Invalid names (SQL injection attempts / malformed)
        assert IrradianceRepository._validate_table_name("table; DROP TABLE users;") is False
        assert IrradianceRepository._validate_table_name("table' OR '1'='1") is False
        assert IrradianceRepository._validate_table_name("table--") is False
        assert IrradianceRepository._validate_table_name("table/*comment*/") is False
        assert IrradianceRepository._validate_table_name("") is False
        assert IrradianceRepository._validate_table_name("123table") is False


class TestDataInsertion:
    """Test data insertion operations."""

    def test_insert_single_record(self, repo):
        """A single inserted record is stored with its values."""
        repo.create_table("measurements")
        repo.insert_measurement("measurements", "2026-06-05", "10:30:00", 750.5)

        with DatabaseManager.get_connection(repo.db_path, use_pool=False) as conn:
            row = conn.execute("SELECT * FROM measurements").fetchone()

        assert row is not None
        assert row[1] == "2026-06-05"  # fecha
        assert row[2] == "10:30:00"  # hora
        assert row[3] == 750.5  # irradiancia

    def test_insert_multiple_records(self, repo):
        """Multiple records are all persisted."""
        repo.create_table("measurements")

        test_data = [
            ("2026-06-05", "10:00:00", 650.0),
            ("2026-06-05", "10:01:00", 720.0),
            ("2026-06-05", "10:02:00", 800.0),
        ]
        for fecha, hora, irradiancia in test_data:
            repo.insert_measurement("measurements", fecha, hora, irradiancia)

        assert _count(repo.db_path, "measurements") == len(test_data)

    def test_insert_with_auto_increment_id(self, repo):
        """Primary key IDs are auto-incremented sequentially."""
        repo.create_table("measurements")

        for i in range(3):
            repo.insert_measurement("measurements", "2026-06-05", f"10:0{i}:00", float(i * 100))

        with DatabaseManager.get_connection(repo.db_path, use_pool=False) as conn:
            ids = [row[0] for row in conn.execute("SELECT id FROM measurements ORDER BY id").fetchall()]

        assert ids == [1, 2, 3]


class TestDataRetrieval:
    """Test data retrieval operations."""

    def test_retrieve_all_records(self, repo):
        """All inserted records are retrievable."""
        repo.create_table("measurements")

        test_count = 5
        for i in range(test_count):
            repo.insert_measurement("measurements", "2026-06-05", f"10:0{i}:00", float(i * 100))

        with DatabaseManager.get_connection(repo.db_path, use_pool=False) as conn:
            rows = conn.execute("SELECT * FROM measurements").fetchall()

        assert len(rows) == test_count

    def test_retrieve_with_filter(self, repo):
        """Records can be filtered with a WHERE clause."""
        repo.create_table("measurements")

        for i in range(10):
            repo.insert_measurement("measurements", "2026-06-05", f"10:{i:02d}:00", float(i * 100))

        with DatabaseManager.get_connection(repo.db_path, use_pool=False) as conn:
            rows = conn.execute("SELECT * FROM measurements WHERE irradiancia > ?", (500.0,)).fetchall()

        # irradiancia values 600, 700, 800, 900
        assert len(rows) == 4
        for row in rows:
            assert row[3] > 500.0

    def test_retrieve_ordered_by_time(self, repo):
        """Records can be retrieved ordered by their time column."""
        repo.create_table("measurements")

        horas = ["10:04:00", "10:00:00", "10:02:00", "10:01:00", "10:03:00"]
        for hora in horas:
            repo.insert_measurement("measurements", "2026-06-05", hora, 0.0)

        with DatabaseManager.get_connection(repo.db_path, use_pool=False) as conn:
            retrieved = [row[0] for row in conn.execute("SELECT hora FROM measurements ORDER BY hora").fetchall()]

        assert retrieved == sorted(horas)

    def test_get_table_statistics(self, repo):
        """Statistics aggregate the irradiance values correctly."""
        repo.create_table("measurements")

        for irradiancia in (650.0, 720.0, 800.0, 850.0):
            repo.insert_measurement("measurements", "2026-06-05", "10:00:00", irradiancia)

        stats = repo.get_statistics("measurements")

        assert stats["count"] == 4
        assert stats["min_irradiancia"] == 650.0
        assert stats["max_irradiancia"] == 850.0
        assert stats["avg_irradiancia"] == pytest.approx(755.0)


class TestDatabaseIntegrity:
    """Test database integrity and constraints."""

    def test_primary_key_autoincrement(self, repo):
        """Each new record gets a distinct, incrementing primary key."""
        repo.create_table("measurements")
        repo.insert_measurement("measurements", "2026-06-05", "10:00:00", 750.5)
        repo.insert_measurement("measurements", "2026-06-05", "10:01:00", 800.0)

        with DatabaseManager.get_connection(repo.db_path, use_pool=False) as conn:
            ids = [row[0] for row in conn.execute("SELECT id FROM measurements ORDER BY id").fetchall()]

        assert ids[1] == ids[0] + 1

    def test_created_at_auto_populated(self, repo):
        """created_at is populated automatically by its DEFAULT."""
        repo.create_table("measurements")
        repo.insert_measurement("measurements", "2026-06-05", "10:00:00", 750.5)

        with DatabaseManager.get_connection(repo.db_path, use_pool=False) as conn:
            created_at = conn.execute("SELECT created_at FROM measurements").fetchone()[0]

        assert created_at is not None

    def test_not_null_constraint_on_irradiancia(self, repo):
        """Inserting without the NOT NULL irradiancia column is rejected."""
        repo.create_table("measurements")

        with pytest.raises(DatabaseError):
            with DatabaseManager.get_connection(repo.db_path, use_pool=False) as conn:
                conn.execute(
                    "INSERT INTO measurements (fecha, hora) VALUES (?, ?)",
                    ("2026-06-05", "10:00:00"),
                )

    def test_concurrent_access(self, repo):
        """Successive connections observe each other's committed writes."""
        repo.create_table("measurements")

        repo.insert_measurement("measurements", "2026-06-05", "10:00:00", 750.5)
        assert _count(repo.db_path, "measurements") == 1

        repo.insert_measurement("measurements", "2026-06-05", "10:01:00", 800.0)
        assert _count(repo.db_path, "measurements") == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
