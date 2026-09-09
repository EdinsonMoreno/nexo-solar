"""Add system metrics table.

Creates the system_metrics table for tracking operational metrics
including uptime, Modbus operation counts, response times, and
database operation statistics.

This migration prepares the database for the metrics and monitoring
system (Phase 4).

Requirements validated: 13.2, 14.4, 14.5
"""

DESCRIPTION = "Add system_metrics table for operational metrics tracking"


def upgrade(conn):
    """Apply the system metrics migration.

    Creates the system_metrics table with columns for tracking:
    - Timestamp of metric collection
    - Metric category (modbus, database, application)
    - Metric name and value
    - Metadata as JSON string

    Args:
        conn: SQLite database connection
    """
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            category TEXT NOT NULL,
            metric_name TEXT NOT NULL,
            metric_value REAL NOT NULL,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create index for efficient queries by category and timestamp
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_metrics_category_timestamp
        ON system_metrics (category, timestamp)
    """)

    # Create index for metric name lookups
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_metrics_name
        ON system_metrics (metric_name)
    """)

    conn.commit()


def downgrade(conn):
    """Reverse the system metrics migration.

    Drops the system_metrics table and its indexes.

    WARNING: This will delete all collected metrics data.

    Args:
        conn: SQLite database connection
    """
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS system_metrics")

    conn.commit()
