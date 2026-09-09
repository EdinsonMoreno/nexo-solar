"""Property-based tests for database migration reversibility.

Property 11: Database Migration Reversibility
Valida: Requisitos 13.2, 13.3, 13.4

This module uses Hypothesis to verify that database migrations are fully
reversible: applying a migration and then rolling it back should restore
the database to its original state.
"""

import gc
import os
import sqlite3
import tempfile

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from modbuspython.migrations.migration_manager import MigrationManager
from modbuspython.data_access.database_manager import SchemaVersionRepository


def create_migration_file(versions_dir, filename, upgrade_sql, downgrade_sql, description="test migration"):
    """Create a migration file in the versions directory."""
    content = (
        f'DESCRIPTION = "{description}"\n'
        "\n"
        "def upgrade(conn):\n"
        f'    conn.execute("""{upgrade_sql}""")\n'
        "\n"
        "def downgrade(conn):\n"
        f'    conn.execute("""{downgrade_sql}""")\n'
    )
    with open(os.path.join(versions_dir, filename), "w") as f:
        f.write(content)


class TestMigrationReversibility:
    """Property 11: Database Migration Reversibility.

    Verify that after applying a migration and then rolling it back,
    the database is restored to its original state.
    """

    @given(
        table_name=st.sampled_from(
            [
                "users",
                "products",
                "orders",
                "logs",
                "metrics",
            ]
        )
    )
    @settings(max_examples=2, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_create_drop_table_is_reversible(self, tmp_path, table_name):
        """Property: CREATE TABLE / DROP TABLE is fully reversible."""
        import uuid

        db_path = str(tmp_path / f"test_{uuid.uuid4().hex[:8]}.db")
        versions_dir = str(tmp_path / "versions")
        os.makedirs(versions_dir, exist_ok=True)

        create_migration_file(
            versions_dir,
            "v1_create_table.py",
            f"CREATE TABLE IF NOT EXISTS {table_name} (id INTEGER PRIMARY KEY, data TEXT)",
            f"DROP TABLE IF EXISTS {table_name}",
            "Create test table",
        )

        manager = MigrationManager(db_path=db_path, migrations_dir=versions_dir)

        # Apply migration
        migrations = manager.discover_migrations()
        assert len(migrations) == 1
        manager.apply_migration(migrations[0])

        # Verify table created
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            assert table_name in tables

        # Rollback
        manager.rollback_migration(migrations[0])

        # Verify table dropped
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            assert table_name not in tables

    @given(column_value=st.text(min_size=1, max_size=10, alphabet="abcdefghijklmnopqrstuvwxyz"))
    @settings(max_examples=2, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_add_column_insert_drop_column_preserves_data(self, tmp_path, column_value):
        """Property: Adding column, inserting data, and rolling back preserves original data."""
        import uuid

        db_path = str(tmp_path / f"test_{uuid.uuid4().hex[:8]}.db")
        versions_dir = str(tmp_path / "versions")
        os.makedirs(versions_dir, exist_ok=True)

        # v1: Create base table
        create_migration_file(
            versions_dir,
            "v1_create_base.py",
            "CREATE TABLE test_data (id INTEGER PRIMARY KEY, name TEXT)",
            "DROP TABLE IF EXISTS test_data",
            "Create base table",
        )

        # v2: Add column
        v2_content = (
            'DESCRIPTION = "Add value column"\n'
            "\n"
            "def upgrade(conn):\n"
            '    conn.execute("ALTER TABLE test_data ADD COLUMN value TEXT")\n'
            "\n"
            "def downgrade(conn):\n"
            '    conn.execute("CREATE TABLE test_data_new (id INTEGER PRIMARY KEY, name TEXT)")\n'
            '    conn.execute("INSERT INTO test_data_new SELECT id, name FROM test_data")\n'
            '    conn.execute("DROP TABLE test_data")\n'
            '    conn.execute("ALTER TABLE test_data_new RENAME TO test_data")\n'
        )
        with open(os.path.join(versions_dir, "v2_add_column.py"), "w") as f:
            f.write(v2_content)

        manager = MigrationManager(db_path=db_path, migrations_dir=versions_dir)

        # Apply v1
        migrations = manager.discover_migrations()
        manager.apply_migration(migrations[0])

        # Insert initial data
        with sqlite3.connect(db_path) as conn:
            conn.execute("INSERT INTO test_data (name) VALUES ('test_row')")
            conn.commit()

        # Apply v2
        manager.apply_migration(migrations[1])

        # Insert data with generated value
        with sqlite3.connect(db_path) as conn:
            conn.execute("INSERT INTO test_data (name, value) VALUES (?, ?)", ("value_row", column_value))
            conn.commit()

        # Rollback v2
        manager.rollback_migration(migrations[1])

        # Verify original data intact
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM test_data WHERE name = 'test_row'")
            result = cursor.fetchone()
            assert result is not None
            assert result[0] == "test_row"

    @given(num_migrations=st.integers(min_value=2, max_value=3))
    @settings(max_examples=2, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_multiple_migrations_round_trip(self, tmp_path, num_migrations):
        """Property: Multiple migrations can be applied and fully rolled back."""
        import uuid

        db_path = str(tmp_path / f"test_{uuid.uuid4().hex[:8]}.db")
        versions_dir = str(tmp_path / "versions")
        os.makedirs(versions_dir, exist_ok=True)

        migrations_data = [
            (
                "v1_create_users.py",
                "Create users table",
                "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)",
                "DROP TABLE IF EXISTS users",
            ),
            (
                "v2_create_posts.py",
                "Create posts table",
                "CREATE TABLE posts (id INTEGER PRIMARY KEY, user_id INTEGER, title TEXT)",
                "DROP TABLE IF EXISTS posts",
            ),
            (
                "v3_create_comments.py",
                "Create comments table",
                "CREATE TABLE comments (id INTEGER PRIMARY KEY, post_id INTEGER, body TEXT)",
                "DROP TABLE IF EXISTS comments",
            ),
        ][:num_migrations]

        for filename, desc, up_sql, down_sql in migrations_data:
            create_migration_file(versions_dir, filename, up_sql, down_sql, desc)

        manager = MigrationManager(db_path=db_path, migrations_dir=versions_dir)

        # Apply all
        manager.apply_all_pending()

        # Verify all tables created
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            for _, desc, _, _ in migrations_data:
                table_name = desc.split()[1].lower()
                assert table_name in tables

        # Rollback all
        manager.rollback_to_version(0)

        # Verify all dropped (except schema_version)
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            assert "schema_version" in tables
            for _, desc, _, _ in migrations_data:
                table_name = desc.split()[1].lower()
                assert table_name not in tables

    @given(num_migrations=st.integers(min_value=1, max_value=3))
    @settings(max_examples=2, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_schema_version_tracks_reversibility(self, tmp_path, num_migrations):
        """Property: Schema version correctly tracks through apply/rollback cycle."""
        import uuid

        db_path = str(tmp_path / f"test_{uuid.uuid4().hex[:8]}.db")
        versions_dir = str(tmp_path / "versions")
        os.makedirs(versions_dir, exist_ok=True)

        for i in range(1, num_migrations + 1):
            create_migration_file(
                versions_dir,
                f"v{i}_migration_{i}.py",
                f"CREATE TABLE IF NOT EXISTS table_v{i} (id INTEGER PRIMARY KEY)",
                f"DROP TABLE IF EXISTS table_v{i}",
                f"Migration v{i}",
            )

        manager = MigrationManager(db_path=db_path, migrations_dir=versions_dir)
        schema_repo = SchemaVersionRepository(db_path)

        # Initial state
        assert schema_repo.get_schema_version() == 0

        # Apply all
        manager.apply_all_pending()
        assert schema_repo.get_schema_version() == num_migrations

        # Rollback each
        migrations = manager.discover_migrations()
        for i in range(num_migrations, 0, -1):
            manager.rollback_migration(migrations[i - 1])
            assert schema_repo.get_schema_version() == i - 1
