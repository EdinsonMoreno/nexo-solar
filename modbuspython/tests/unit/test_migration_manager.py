"""Tests for the MigrationManager system.

Tests cover:
- Migration discovery and loading
- Applying migrations
- Rolling back migrations
- Error handling
- Pending migration detection

Requirements validated: 13.2, 13.3, 13.4, 13.5
"""

import os
import sqlite3
import tempfile
import pytest
from unittest.mock import Mock, patch

from modbuspython.migrations.migration_manager import MigrationManager, MigrationModule, MigrationInfo, MigrationStatus
from modbuspython.exceptions import MigrationError
from modbuspython.data_access.database_manager import SchemaVersionRepository


@pytest.fixture
def temp_db():
    """Create a temporary database file for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def temp_migrations_dir(tmp_path):
    """Create a temporary migrations directory with test migrations."""
    versions_dir = tmp_path / "versions"
    versions_dir.mkdir()

    # Create v1 migration
    v1_content = """
DESCRIPTION = "Create test table"

def upgrade(conn):
    conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT)")

def downgrade(conn):
    conn.execute("DROP TABLE IF EXISTS test_table")
"""
    (versions_dir / "v1_create_test_table.py").write_text(v1_content)

    # Create v2 migration
    v2_content = '''
DESCRIPTION = "Add status column"

def upgrade(conn):
    conn.execute("ALTER TABLE test_table ADD COLUMN status TEXT DEFAULT 'active'")

def downgrade(conn):
    # SQLite doesn't support DROP COLUMN directly, recreate table
    conn.execute("""
        CREATE TABLE test_table_new (id INTEGER PRIMARY KEY, name TEXT)
    """)
    conn.execute("INSERT INTO test_table_new SELECT id, name FROM test_table")
    conn.execute("DROP TABLE test_table")
    conn.execute("ALTER TABLE test_table_new RENAME TO test_table")
'''
    (versions_dir / "v2_add_status_column.py").write_text(v2_content)

    # Create v3 migration
    v3_content = """
DESCRIPTION = "Create index on name"

def upgrade(conn):
    conn.execute("CREATE INDEX IF NOT EXISTS idx_test_name ON test_table (name)")

def downgrade(conn):
    conn.execute("DROP INDEX IF EXISTS idx_test_name")
"""
    (versions_dir / "v3_create_index.py").write_text(v3_content)

    return str(versions_dir)


@pytest.fixture
def migration_manager(temp_db, temp_migrations_dir):
    """Create a MigrationManager instance with temp database and migrations."""
    return MigrationManager(db_path=temp_db, migrations_dir=temp_migrations_dir)


class TestMigrationDiscovery:
    """Tests for migration discovery and loading."""

    def test_discover_migrations_finds_all_files(self, migration_manager):
        """Test that discover_migrations finds all valid migration files."""
        migrations = migration_manager.discover_migrations()
        assert len(migrations) == 3
        assert migrations[0].version == 1
        assert migrations[1].version == 2
        assert migrations[2].version == 3

    def test_discover_migrations_sorted_by_version(self, migration_manager):
        """Test that migrations are returned sorted by version."""
        migrations = migration_manager.discover_migrations()
        versions = [m.version for m in migrations]
        assert versions == sorted(versions)

    def test_discover_migrations_empty_directory(self, temp_db, tmp_path):
        """Test discovery with empty migrations directory."""
        empty_dir = str(tmp_path / "empty_versions")
        os.makedirs(empty_dir, exist_ok=True)
        manager = MigrationManager(db_path=temp_db, migrations_dir=empty_dir)
        migrations = manager.discover_migrations()
        assert len(migrations) == 0

    def test_discover_migrations_nonexistent_directory(self, temp_db):
        """Test discovery with non-existent migrations directory."""
        manager = MigrationManager(db_path=temp_db, migrations_dir="/nonexistent/path")
        migrations = manager.discover_migrations()
        assert len(migrations) == 0

    def test_load_migration_with_missing_upgrade(self, temp_db, tmp_path):
        """Test that loading fails if migration lacks upgrade function."""
        versions_dir = tmp_path / "versions"
        versions_dir.mkdir()
        (versions_dir / "v1_bad_migration.py").write_text("def downgrade(conn): pass\n")
        manager = MigrationManager(db_path=temp_db, migrations_dir=str(versions_dir))
        with pytest.raises(MigrationError, match="missing upgrade"):
            manager.discover_migrations()

    def test_load_migration_with_missing_downgrade(self, temp_db, tmp_path):
        """Test that loading fails if migration lacks downgrade function."""
        versions_dir = tmp_path / "versions"
        versions_dir.mkdir()
        (versions_dir / "v1_bad_migration.py").write_text("def upgrade(conn): pass\n")
        manager = MigrationManager(db_path=temp_db, migrations_dir=str(versions_dir))
        with pytest.raises(MigrationError, match="missing downgrade"):
            manager.discover_migrations()


class TestPendingMigrations:
    """Tests for pending migration detection."""

    def test_get_pending_migrations_all_pending(self, migration_manager):
        """Test that all migrations are pending on fresh database."""
        pending = migration_manager.get_pending_migrations()
        assert len(pending) == 3

    def test_get_pending_migrations_after_apply(self, migration_manager):
        """Test pending detection after applying some migrations."""
        migration_manager.apply_all_pending()
        pending = migration_manager.get_pending_migrations()
        assert len(pending) == 0

    def test_get_pending_migrations_partial_apply(self, migration_manager):
        """Test pending detection after partial migration."""
        migrations = migration_manager.discover_migrations()
        migration_manager.apply_migration(migrations[0])
        migration_manager.apply_migration(migrations[1])

        pending = migration_manager.get_pending_migrations()
        assert len(pending) == 1
        assert pending[0].version == 3


class TestApplyMigration:
    """Tests for applying migrations."""

    def test_apply_single_migration(self, migration_manager):
        """Test applying a single migration."""
        migrations = migration_manager.discover_migrations()
        result = migration_manager.apply_migration(migrations[0])

        assert result is True
        schema_repo = SchemaVersionRepository(migration_manager.db_path)
        assert schema_repo.get_schema_version() == 1

    def test_apply_migration_creates_table(self, migration_manager):
        """Test that applying migration actually creates the table."""
        migrations = migration_manager.discover_migrations()
        migration_manager.apply_migration(migrations[0])

        with sqlite3.connect(migration_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'")
            result = cursor.fetchone()
            assert result is not None

    def test_apply_all_pending(self, migration_manager):
        """Test applying all pending migrations at once."""
        applied = migration_manager.apply_all_pending()

        assert len(applied) == 3
        assert applied == [1, 2, 3]

        schema_repo = SchemaVersionRepository(migration_manager.db_path)
        assert schema_repo.get_schema_version() == 3

    def test_apply_all_pending_nothing_to_apply(self, migration_manager):
        """Test applying when no migrations are pending."""
        migration_manager.apply_all_pending()
        applied = migration_manager.apply_all_pending()
        assert len(applied) == 0

    def test_apply_migration_with_error_rolls_back(self, temp_db, tmp_path):
        """Test that failed migration rolls back transaction."""
        versions_dir = tmp_path / "versions"
        versions_dir.mkdir()
        (versions_dir / "v1_failing_migration.py").write_text(
            "def upgrade(conn):\n"
            "    conn.execute('CREATE TABLE test (id INTEGER PRIMARY KEY)')\n"
            "    raise RuntimeError('Intentional failure')\n"
            "def downgrade(conn):\n"
            "    conn.execute('DROP TABLE IF EXISTS test')\n"
        )
        manager = MigrationManager(db_path=temp_db, migrations_dir=str(versions_dir))
        migrations = manager.discover_migrations()

        with pytest.raises(MigrationError, match="Intentional failure"):
            manager.apply_migration(migrations[0])

        # Verify table was not created (transaction rolled back)
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='test'")
            assert cursor.fetchone() is None


class TestRollbackMigration:
    """Tests for rolling back migrations."""

    def test_rollback_single_migration(self, migration_manager):
        """Test rolling back the latest applied migration."""
        migration_manager.apply_all_pending()
        migrations = migration_manager.discover_migrations()

        result = migration_manager.rollback_migration(migrations[2])
        assert result is True

        schema_repo = SchemaVersionRepository(migration_manager.db_path)
        assert schema_repo.get_schema_version() == 2

    def test_rollback_removes_table(self, migration_manager):
        """Test that rollback properly removes created objects."""
        migration_manager.apply_all_pending()
        migrations = migration_manager.discover_migrations()

        # Verify index exists
        with sqlite3.connect(migration_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_test_name'")
            assert cursor.fetchone() is not None

        # Rollback v3 (index creation)
        migration_manager.rollback_migration(migrations[2])

        # Verify index was removed
        with sqlite3.connect(migration_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_test_name'")
            assert cursor.fetchone() is None

    def test_rollback_wrong_version_raises_error(self, migration_manager):
        """Test that rolling back non-latest migration raises error."""
        migration_manager.apply_all_pending()
        migrations = migration_manager.discover_migrations()

        # Try to rollback v1 when v3 is current
        with pytest.raises(MigrationError, match="current version is"):
            migration_manager.rollback_migration(migrations[0])

    def test_rollback_to_version(self, migration_manager):
        """Test rolling back to a specific version."""
        migration_manager.apply_all_pending()

        rolled_back = migration_manager.rollback_to_version(1)

        assert rolled_back == [3, 2]
        schema_repo = SchemaVersionRepository(migration_manager.db_path)
        assert schema_repo.get_schema_version() == 1

    def test_rollback_to_same_version(self, migration_manager):
        """Test rollback to current version does nothing."""
        migration_manager.apply_all_pending()

        rolled_back = migration_manager.rollback_to_version(3)
        assert len(rolled_back) == 0


class TestMigrationStatus:
    """Tests for migration status reporting."""

    def test_get_migration_status_initial(self, migration_manager):
        """Test status on fresh database with no migrations applied."""
        status = migration_manager.get_migration_status()

        assert status["current_version"] == 0
        assert status["total_migrations"] == 3
        assert status["pending_count"] == 3
        assert status["applied_count"] == 0

    def test_get_migration_status_after_apply(self, migration_manager):
        """Test status after applying all migrations."""
        migration_manager.apply_all_pending()
        status = migration_manager.get_migration_status()

        assert status["current_version"] == 3
        assert status["latest_version"] == 3
        assert status["pending_count"] == 0
        assert status["applied_count"] == 3

    def test_get_migration_status_partial(self, migration_manager):
        """Test status after applying some migrations."""
        migrations = migration_manager.discover_migrations()
        migration_manager.apply_migration(migrations[0])
        migration_manager.apply_migration(migrations[1])

        status = migration_manager.get_migration_status()
        assert status["current_version"] == 2
        assert status["pending_count"] == 1
        assert status["applied_count"] == 2

    def test_get_applied_migrations(self, migration_manager):
        """Test getting list of all migrations with status."""
        migration_manager.apply_migration(migration_manager.discover_migrations()[0])
        infos = migration_manager.get_applied_migrations()

        assert len(infos) == 3
        assert infos[0].status == MigrationStatus.APPLIED
        assert infos[1].status == MigrationStatus.PENDING
        assert infos[2].status == MigrationStatus.PENDING


class TestMigrationErrorHandling:
    """Tests for migration error scenarios."""

    def test_migration_with_invalid_sql(self, temp_db, tmp_path):
        """Test handling of migrations with invalid SQL."""
        versions_dir = tmp_path / "versions"
        versions_dir.mkdir()
        (versions_dir / "v1_bad_sql.py").write_text(
            "def upgrade(conn):\n" "    conn.execute('INVALID SQL STATEMENT')\n" "def downgrade(conn): pass\n"
        )
        manager = MigrationManager(db_path=temp_db, migrations_dir=str(versions_dir))
        migrations = manager.discover_migrations()

        with pytest.raises(MigrationError):
            manager.apply_migration(migrations[0])

    def test_schema_version_updated_after_successful_migration(self, migration_manager):
        """Test that schema version is only updated after successful migration."""
        migrations = migration_manager.discover_migrations()
        migration_manager.apply_migration(migrations[0])

        schema_repo = SchemaVersionRepository(migration_manager.db_path)
        assert schema_repo.get_schema_version() == 1

    def test_migrate_to_latest_convenience_method(self, migration_manager):
        """Test migrate_to_latest applies all pending."""
        applied = migration_manager.migrate_to_latest()
        assert applied == [1, 2, 3]
