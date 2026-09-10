"""Initial schema migration.

Creates the base tables required by Nexo Solar:
- irradiance measurements table (generic structure)
- schema_version table (for migration tracking)

This is the baseline migration (v1) that establishes the initial database structure.

Requirements validated: 13.2, 13.6
"""

DESCRIPTION = "Initial schema: creates base tables for Nexo Solar"


def upgrade(conn):
    """Apply the initial schema migration.

    Creates the schema_version table for tracking migrations and
    the base irradiance measurements table.

    Args:
        conn: SQLite database connection
    """
    cursor = conn.cursor()

    # Create schema_version table for migration tracking
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            version INTEGER NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            description TEXT
        )
    """)

    # Initialize with version 0 if empty
    cursor.execute("SELECT COUNT(*) FROM schema_version")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO schema_version (id, version, description)
            VALUES (1, 1, 'Initial schema migration')
        """)

    # Create irradiance measurements table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mediciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            hora TEXT NOT NULL,
            irradiancia REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()


def downgrade(conn):
    """Reverse the initial schema migration.

    Drops all tables created by this migration.

    WARNING: This will delete all data in the database.

    Args:
        conn: SQLite database connection
    """
    cursor = conn.cursor()

    # Drop tables in reverse dependency order
    cursor.execute("DROP TABLE IF EXISTS mediciones")
    cursor.execute("DROP TABLE IF EXISTS schema_version")

    conn.commit()
