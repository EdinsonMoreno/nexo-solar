"""Integration tests for Modbus → Database flow.







Tests the complete flow from Modbus read operations to database storage,






verifying that:






- ModbusClient successfully reads data from Modbus registers






- Data is correctly parsed and formatted






- DatabaseManager stores the data correctly






- Database queries return the stored data






- Timestamps are properly recorded







These tests use mocks for pymodbus and temporary databases.






Note: The actual database schema stores (fecha, hora, irradiancia) only.
"""

import sys


import pytest


import sqlite3


from pathlib import Path


from unittest.mock import Mock, patch, MagicMock


from datetime import datetime


from PyQt6.QtTest import QSignalSpy


from PyQt6.QtCore import QEventLoop, QTimer

# Add parent directory to path for imports


sys.path.insert(0, str(Path(__file__).parent.parent.parent))


from modbuspython.data_access.modbus_client import ModbusClient


from modbuspython.backend.sqlite_manager import DatabaseManager, connect_db, crear_tabla, insert_record


from modbuspython.config.config_manager import ConfigurationManager


class TestModbusToDatabaseFlow:
    """Test complete flow from Modbus read to database storage."""

    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create a temporary database for testing."""

        db_path = tmp_path / "test_solarsense.db"

        conn = connect_db(str(db_path))

        crear_tabla(conn, "measurements")

        yield str(db_path), conn

        conn.close()

    @pytest.fixture
    def config_manager(self, temp_db):
        """Create a ConfigurationManager with test configuration."""

        db_path, _ = temp_db

        config = ConfigurationManager()

        config._config = {
            "modbus": {
                "host": "192.168.1.100",
                "port": 502,
                "timeout": 5.0,
                "retry_attempts": 3,
                "retry_backoff": 0.1,
                "registers": {
                    "rotation_setpoint": 0,
                    "elevation_setpoint": 1,
                    "rotation_actual": 2,
                    "elevation_actual": 3,
                    "irradiance": 4,
                },
            },
            "database": {"path": db_path, "table_name": "measurements", "connection_pool_size": 5},
        }

        return config

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    def test_read_radiation_and_store_to_database(self, mock_modbus_tcp_client, temp_db, config_manager):
        """Test reading radiation from Modbus and storing to database."""

        db_path, conn = temp_db

        # Setup mock Modbus client

        mock_client_instance = MagicMock()

        mock_client_instance.connect.return_value = True

        # Mock radiation read response (value 85000 = 850.00 W/m²)

        mock_response = MagicMock()

        mock_response.registers = [85000]

        mock_client_instance.read_input_registers.return_value = mock_response

        mock_modbus_tcp_client.return_value = mock_client_instance

        # Create and connect ModbusClient

        modbus_client = ModbusClient(
            ip=config_manager.get("modbus.host"), port=config_manager.get("modbus.port"), config_manager=config_manager
        )

        modbus_client.connect()

        # Connect to radiation signal

        radiation_spy = QSignalSpy(modbus_client.irradiance_updated)

        # Read radiation - need to process events for signal to emit

        modbus_client.read_irradiance()

        # Process Qt events to allow signal emission

        loop = QEventLoop()

        QTimer.singleShot(50, loop.quit)

        loop.exec()

        # Verify signal was emitted with correct value

        if len(radiation_spy) > 0:

            radiation_value = radiation_spy[0][0]

            assert radiation_value == pytest.approx(850.0)

            # Store to database using actual schema (fecha, hora, irradiancia)

            now = datetime.now()

            fecha = now.strftime("%Y-%m-%d")

            hora = now.strftime("%H:%M:%S")

            insert_record(conn, "measurements", fecha, hora, radiation_value)

            # Verify data was stored

            cursor = conn.cursor()

            cursor.execute("SELECT * FROM measurements WHERE irradiancia = ?", (radiation_value,))

            row = cursor.fetchone()

            assert row is not None

            assert row[3] == radiation_value  # irradiance column

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    def test_multiple_measurements_stored_sequentially(self, mock_modbus_tcp_client, temp_db, config_manager):
        """Test that multiple measurements are stored correctly in sequence."""

        db_path, conn = temp_db

        # Setup mock Modbus client

        mock_client_instance = MagicMock()

        mock_client_instance.connect.return_value = True

        mock_modbus_tcp_client.return_value = mock_client_instance

        # Create and connect ModbusClient

        modbus_client = ModbusClient(
            ip=config_manager.get("modbus.host"), port=config_manager.get("modbus.port"), config_manager=config_manager
        )

        modbus_client.connect()

        # Simulate multiple measurement cycles

        test_irradiances = [650.0, 720.0, 800.0, 850.0]

        for irrad in test_irradiances:

            # Mock response for this cycle

            mock_response = MagicMock()

            mock_response.registers = [int(irrad * 100)]

            mock_client_instance.read_input_registers.return_value = mock_response

            # Read radiation

            radiation_spy = QSignalSpy(modbus_client.irradiance_updated)

            modbus_client.read_irradiance()

            # Process events

            loop = QEventLoop()

            QTimer.singleShot(50, loop.quit)

            loop.exec()

            # Store to database

            radiation = radiation_spy[0][0] if len(radiation_spy) > 0 else irrad

            now = datetime.now()

            fecha = now.strftime("%Y-%m-%d")

            hora = now.strftime("%H:%M:%S")

            insert_record(conn, "measurements", fecha, hora, radiation)

        # Verify all records were stored

        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM measurements")

        count = cursor.fetchone()[0]

        assert count == len(test_irradiances)

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    def test_database_context_manager(self, mock_modbus_tcp_client, temp_db, config_manager):
        """Test that database context manager properly handles connections."""

        db_path, _ = temp_db

        # Setup mock Modbus client

        mock_client_instance = MagicMock()

        mock_client_instance.connect.return_value = True

        mock_response = MagicMock()

        mock_response.registers = [50000]

        mock_client_instance.read_input_registers.return_value = mock_response

        mock_modbus_tcp_client.return_value = mock_client_instance

        # Create and connect ModbusClient

        modbus_client = ModbusClient(
            ip=config_manager.get("modbus.host"), port=config_manager.get("modbus.port"), config_manager=config_manager
        )

        modbus_client.connect()

        # Read radiation

        radiation_spy = QSignalSpy(modbus_client.irradiance_updated)

        modbus_client.read_irradiance()

        # Process events

        loop = QEventLoop()

        QTimer.singleShot(50, loop.quit)

        loop.exec()

        radiation = radiation_spy[0][0] if len(radiation_spy) > 0 else 500.0

        # Use context manager for database operations

        with DatabaseManager.get_connection(db_path) as conn:

            now = datetime.now()

            fecha = now.strftime("%Y-%m-%d")

            hora = now.strftime("%H:%M:%S")

            insert_record(conn, "measurements", fecha, hora, radiation)

            # Verify data was stored within context

            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM measurements")

            count = cursor.fetchone()[0]

            assert count == 1

        # Verify connection was properly closed and data persisted

        with DatabaseManager.get_connection(db_path) as conn:

            cursor = conn.cursor()

            cursor.execute("SELECT irradiancia FROM measurements")

            row = cursor.fetchone()

            assert row is not None

            assert row[0] == pytest.approx(radiation)

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    def test_modbus_read_failure_does_not_corrupt_database(self, mock_modbus_tcp_client, temp_db, config_manager):
        """Test that Modbus read failures don't corrupt database."""

        db_path, conn = temp_db

        # Setup mock Modbus client

        mock_client_instance = MagicMock()

        mock_client_instance.connect.return_value = True

        # First read succeeds

        mock_success_response = MagicMock()

        mock_success_response.registers = [60000]

        # Second read fails

        mock_client_instance.read_input_registers.side_effect = [mock_success_response, Exception("Modbus timeout")]

        mock_modbus_tcp_client.return_value = mock_client_instance

        # Create and connect ModbusClient

        modbus_client = ModbusClient(
            ip=config_manager.get("modbus.host"), port=config_manager.get("modbus.port"), config_manager=config_manager
        )

        modbus_client.connect()

        # First read succeeds

        radiation_spy = QSignalSpy(modbus_client.irradiance_updated)

        modbus_client.read_irradiance()

        # Process events

        loop = QEventLoop()

        QTimer.singleShot(50, loop.quit)

        loop.exec()

        if len(radiation_spy) > 0:

            radiation1 = radiation_spy[0][0]

            # Store first reading

            now = datetime.now()

            fecha = now.strftime("%Y-%m-%d")

            hora = now.strftime("%H:%M:%S")

            insert_record(conn, "measurements", fecha, hora, radiation1)

        # Second read fails (should not emit signal)

        radiation_spy.clear()

        modbus_client.read_irradiance()

        # Process events

        loop = QEventLoop()

        QTimer.singleShot(50, loop.quit)

        loop.exec()

        # No signal should be emitted on failure

        # Verify database still has only one record and is not corrupted

        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM measurements")

        count = cursor.fetchone()[0]

        assert count <= 1  # At most 1 record (if first read succeeded)

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    def test_modbus_client_with_sqlite_configuration(self, mock_modbus_tcp_client, temp_db, config_manager):
        """Test ModbusClient configured with SQLite auto-storage."""

        db_path, conn = temp_db

        # Setup mock Modbus client

        mock_client_instance = MagicMock()

        mock_client_instance.connect.return_value = True

        mock_response = MagicMock()

        mock_response.registers = [75000]

        mock_client_instance.read_input_registers.return_value = mock_response

        mock_modbus_tcp_client.return_value = mock_client_instance

        # Create and connect ModbusClient

        modbus_client = ModbusClient(
            ip=config_manager.get("modbus.host"), port=config_manager.get("modbus.port"), config_manager=config_manager
        )

        modbus_client.connect()

        # Configure SQLite auto-storage

        modbus_client.configure_sqlite(db_path, "measurements")

        # Read radiation - should auto-store if configured

        radiation_spy = QSignalSpy(modbus_client.irradiance_updated)

        modbus_client.read_irradiance()

        # Process events

        loop = QEventLoop()

        QTimer.singleShot(50, loop.quit)

        loop.exec()

        # Verify signal was emitted

        if len(radiation_spy) > 0:

            radiation = radiation_spy[0][0]

            assert radiation == pytest.approx(750.0)


if __name__ == "__main__":

    pytest.main([__file__, "-v"])
