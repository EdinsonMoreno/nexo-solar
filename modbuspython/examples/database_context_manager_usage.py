"""


Example usage of DatabaseManager context manager.



This demonstrates the recommended way to interact with the database


using the context manager pattern for automatic resource cleanup.
"""

from modbuspython.backend.sqlite_manager import DatabaseManager, crear_tabla, insert_record, get_table_statistics


def example_basic_usage():
    """Basic usage: automatic commit and connection cleanup."""

    db_path = "data/irradiancia.db"

    table_name = "lecturas_irradiancia"

    # Context manager automatically handles connection lifecycle

    with DatabaseManager.get_connection(db_path) as conn:

        # Create table if it doesn't exist

        crear_tabla(conn, table_name)

        # Insert a record

        insert_record(conn, table_name, "2024-03-12", "14:30:00", 875.3)

        # Transaction is automatically committed when exiting the context

    print("✓ Data inserted and committed successfully")


def example_multiple_operations():
    """Multiple operations in a single transaction."""

    db_path = "data/irradiancia.db"

    table_name = "lecturas_irradiancia"

    with DatabaseManager.get_connection(db_path) as conn:

        # All operations are part of the same transaction

        insert_record(conn, table_name, "2024-03-12", "15:00:00", 890.1)

        insert_record(conn, table_name, "2024-03-12", "15:30:00", 905.7)

        insert_record(conn, table_name, "2024-03-12", "16:00:00", 850.2)

        # Get statistics

        stats = get_table_statistics(conn, table_name)

        print(f"Total records: {stats['count']}")

        print(f"Average irradiance: {stats['avg_irradiancia']:.2f} W/m²")

        # All changes committed automatically on successful exit


def example_error_handling():
    """Automatic rollback on error."""

    db_path = "data/irradiancia.db"

    table_name = "lecturas_irradiancia"

    try:

        with DatabaseManager.get_connection(db_path) as conn:

            # Insert some data

            insert_record(conn, table_name, "2024-03-12", "17:00:00", 820.5)

            # Simulate an error

            raise ValueError("Something went wrong!")

            # This line won't be reached

            insert_record(conn, table_name, "2024-03-12", "17:30:00", 800.0)

    except ValueError as e:

        print(f"✓ Error occurred: {e}")

        print("✓ Transaction was automatically rolled back")

        print("✓ Connection was automatically closed")


def example_manual_transaction_control():
    """Manual transaction control with auto_commit=False."""

    db_path = "data/irradiancia.db"

    table_name = "lecturas_irradiancia"

    with DatabaseManager.get_connection(db_path, auto_commit=False) as conn:

        try:

            # Perform operations

            insert_record(conn, table_name, "2024-03-12", "18:00:00", 750.3)

            insert_record(conn, table_name, "2024-03-12", "18:30:00", 720.8)

            # Manually commit when ready

            conn.commit()

            print("✓ Manual commit successful")

        except Exception as e:

            # Manually rollback on error

            conn.rollback()

            print(f"✗ Error occurred, rolled back: {e}")


def example_read_only_operations():
    """Read-only operations don't need auto_commit."""

    db_path = "data/irradiancia.db"

    table_name = "lecturas_irradiancia"

    # For read-only, auto_commit doesn't matter but can be disabled for clarity

    with DatabaseManager.get_connection(db_path, auto_commit=False) as conn:

        cursor = conn.cursor()

        # Query data

        cursor.execute(f"""


            SELECT fecha, hora, irradiancia


            FROM {table_name}


            ORDER BY fecha DESC, hora DESC


            LIMIT 10
        """)

        records = cursor.fetchall()

        print(f"✓ Retrieved {len(records)} recent records")

        for fecha, hora, irradiancia in records:

            print(f"  {fecha} {hora}: {irradiancia} W/m²")


if __name__ == "__main__":

    print("DatabaseManager Context Manager Examples\n")

    print("=" * 50)

    print("\n1. Basic Usage:")

    example_basic_usage()

    print("\n2. Multiple Operations:")

    example_multiple_operations()

    print("\n3. Error Handling:")

    example_error_handling()

    print("\n4. Manual Transaction Control:")

    example_manual_transaction_control()

    print("\n5. Read-Only Operations:")

    example_read_only_operations()

    print("\n" + "=" * 50)

    print("All examples completed!")
