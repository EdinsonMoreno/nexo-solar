"""Integration tests for error handling verification (Task 12.2).







Tests verify that the system handles failures gracefully and continues operating:






- Requirement 4.1: Modbus connection failure handling






- Requirement 4.2: Modbus read operation failure handling






- Requirement 4.3: Modbus write operation failure with retry






- Requirement 4.4: SQLite operation failure handling







These tests simulate real failure scenarios to ensure robustness.
"""

import sys


import pytest


from pathlib import Path


from unittest.mock import Mock, patch, MagicMock


from PyQt6.QtTest import QSignalSpy


import sqlite3
import tempfile
import os

# Add parent directory to path for imports


sys.path.insert(0, str(Path(__file__).parent.parent.parent))


from modbuspython.data_access.modbus_client import ModbusClient


from modbuspython.backend import sqlite_manager


from modbuspython.exceptions import ModbusConnectionError, ModbusOperationError, DatabaseError


class TestModbusConnectionFailure:
    """Test Requirement 4.1: Modbus connection failure handling."""

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    def test_connection_failure_logs_error_and_attempts_reconnection(self, mock_modbus_tcp_client):
        """






        Validates: Requirement 4.1







        When Modbus connection fails, the module should log error with details
        and attempt reconnection.
        """

        # Setup mock to fail connection

        mock_client_instance = MagicMock()

        mock_client_instance.connect.return_value = False

        mock_modbus_tcp_client.return_value = mock_client_instance

        # Create ModbusClient with retry configuration

        from modbuspython.config.config_manager import ConfigurationManager

        config = ConfigurationManager()

        config._config = {"modbus": {"retry_attempts": 3, "retry_backoff": 0.1, "timeout": 5.0}}

        client = ModbusClient(ip="192.168.1.100", port=502, config_manager=config)

        # Connect to signals

        connection_spy = QSignalSpy(client.conexion_cambiada)

        log_spy = QSignalSpy(client.log)

        # Attempt connection

        client.connect()

        # Verify connection was attempted multiple times (retry logic)

        assert mock_client_instance.connect.call_count == 3

        # Verify connection state is False

        assert client.is_connected is False

        # Verify signal was emitted

        assert len(connection_spy) == 1

        assert connection_spy[0][0] is False

        # Verify logging occurred (log signal was emitted)

        assert len(log_spy) > 0

        # Verify system continues operating (no exception raised)

        # System should be in safe state but not crashed

        assert client.is_in_safe_state() is True

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    def test_connection_exception_handled_gracefully(self, mock_modbus_tcp_client):
        """






        Validates: Requirement 4.1







        When Modbus connection raises exception, system should handle it






        gracefully and continue operating.
        """

        # Setup mock to raise exception

        mock_modbus_tcp_client.side_effect = OSError("Network unreachable")

        # Create ModbusClient

        client = ModbusClient(ip="192.168.1.100", port=502)

        # Connect to signals

        connection_spy = QSignalSpy(client.conexion_cambiada)

        log_spy = QSignalSpy(client.log)

        # Attempt connection (should not raise exception)

        client.connect()

        # Verify connection state is False

        assert client.is_connected is False

        # Verify signal was emitted

        assert len(connection_spy) == 1

        assert connection_spy[0][0] is False

        # Verify error was logged

        assert len(log_spy) > 0

        # Verify system continues operating

        assert client.is_in_safe_state() is True


class TestModbusReadFailure:
    """Test Requirement 4.2: Modbus read operation failure handling."""

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    def test_read_failure_logs_error_and_continues(self, mock_modbus_tcp_client):
        """






        Validates: Requirement 4.2







        When Modbus read operation fails, the module should log error






        and continue operation without crashing.
        """

        # Setup mock

        mock_client_instance = MagicMock()

        mock_client_instance.connect.return_value = True

        # Mock read to always fail

        mock_client_instance.read_input_registers.side_effect = Exception("Read timeout")

        mock_modbus_tcp_client.return_value = mock_client_instance

        # Create ModbusClient with retry configuration

        from modbuspython.config.config_manager import ConfigurationManager

        config = ConfigurationManager()

        config._config = {"modbus": {"retry_attempts": 3, "retry_backoff": 0.1, "timeout": 5.0}}

        client = ModbusClient(ip="192.168.1.100", port=502, config_manager=config)

        client.connect()

        # Connect to signals

        radiation_spy = QSignalSpy(client.irradiance_updated)

        log_spy = QSignalSpy(client.log)

        connection_spy = QSignalSpy(client.conexion_cambiada)

        # Attempt to read radiation (should not crash)

        client.read_irradiance()

        # Verify read was attempted multiple times (retry logic)

        assert mock_client_instance.read_input_registers.call_count == 3

        # Verify no radiation signal was emitted (read failed)

        assert len(radiation_spy) == 0

        # Verify error was logged

        assert len(log_spy) > 0

        # Verify system continues operating (connection marked as failed)

        assert client.is_connected is False

        # Verify connection changed signal was emitted

        assert len(connection_spy) >= 1

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    def test_read_with_invalid_response_continues_operation(self, mock_modbus_tcp_client):
        """






        Validates: Requirement 4.2







        When Modbus read returns invalid response, system should log error






        and continue without crashing.
        """

        # Setup mock

        mock_client_instance = MagicMock()

        mock_client_instance.connect.return_value = True

        # Mock read to return None (invalid response)

        mock_client_instance.read_input_registers.return_value = None

        mock_modbus_tcp_client.return_value = mock_client_instance

        # Create ModbusClient

        from modbuspython.config.config_manager import ConfigurationManager

        config = ConfigurationManager()

        config._config = {"modbus": {"retry_attempts": 2, "retry_backoff": 0.1, "timeout": 5.0}}

        client = ModbusClient(ip="192.168.1.100", port=502, config_manager=config)

        client.connect()

        # Connect to signals

        radiation_spy = QSignalSpy(client.irradiance_updated)

        log_spy = QSignalSpy(client.log)

        # Attempt to read radiation

        client.read_irradiance()

        # Verify no radiation signal was emitted

        assert len(radiation_spy) == 0

        # Verify error was logged

        assert len(log_spy) > 0

        # Verify system continues operating

        # (connection may be marked as failed after retries)


class TestModbusWriteFailure:
    """Test Requirement 4.3: Modbus write operation failure with retry."""

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    def test_write_failure_retries_up_to_3_times(self, mock_modbus_tcp_client):
        """






        Validates: Requirement 4.3







        When Modbus write operation fails, the module should log error






        and retry up to 3 times.
        """

        # Setup mock

        mock_client_instance = MagicMock()

        mock_client_instance.connect.return_value = True

        # Mock write to always fail

        mock_client_instance.write_register.side_effect = Exception("Write timeout")

        mock_modbus_tcp_client.return_value = mock_client_instance

        # Create ModbusClient with retry configuration

        from modbuspython.config.config_manager import ConfigurationManager

        config = ConfigurationManager()

        config._config = {"modbus": {"retry_attempts": 3, "retry_backoff": 0.1, "timeout": 5.0}}

        client = ModbusClient(ip="192.168.1.100", port=502, config_manager=config)

        client.connect()

        # Connect to signals

        log_spy = QSignalSpy(client.log)

        retry_spy = QSignalSpy(client.retry_exhausted)

        # Attempt to write setpoints

        client.write_setpoints(90, 45)

        # Verify write was attempted 3 times (retry logic wraps the entire write operation)

        # The retry strategy retries the whole operation, not individual register writes

        assert mock_client_instance.write_register.call_count >= 3

        # Verify error was logged

        assert len(log_spy) > 0

        # Verify retry exhausted signal was emitted

        assert len(retry_spy) == 1

        # Verify system enters safe state after retry exhaustion

        assert client.is_in_safe_state() is True

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    def test_write_succeeds_on_retry(self, mock_modbus_tcp_client):
        """






        Validates: Requirement 4.3







        When Modbus write fails initially but succeeds on retry,






        operation should complete successfully.
        """

        # Setup mock

        mock_client_instance = MagicMock()

        mock_client_instance.connect.return_value = True

        # Mock write to fail first time, succeed second time

        mock_success_response = MagicMock()

        mock_success_response.isError.return_value = False

        mock_client_instance.write_register.side_effect = [
            Exception("Timeout"),  # First attempt fails (motor1)
            Exception("Timeout"),  # First attempt fails (motor2)
            mock_success_response,  # Second attempt succeeds (motor1)
            mock_success_response,  # Second attempt succeeds (motor2)
        ]

        mock_modbus_tcp_client.return_value = mock_client_instance

        # Create ModbusClient

        from modbuspython.config.config_manager import ConfigurationManager

        config = ConfigurationManager()

        config._config = {"modbus": {"retry_attempts": 3, "retry_backoff": 0.1, "timeout": 5.0}}

        client = ModbusClient(ip="192.168.1.100", port=502, config_manager=config)

        client.connect()

        # Connect to signals

        log_spy = QSignalSpy(client.log)

        # Attempt to write setpoints

        client.write_setpoints(90, 45)

        # Verify write was attempted twice (4 total calls: 2 registers * 2 attempts)

        assert mock_client_instance.write_register.call_count == 4

        # Verify success was logged

        assert len(log_spy) > 0

        # Verify system is NOT in safe state (operation succeeded)

        assert client.is_in_safe_state() is False


class TestSQLiteFailure:
    """Test Requirement 4.4: SQLite operation failure handling."""

    def test_sqlite_connection_failure_logs_and_continues(self):
        """






        Validates: Requirement 4.4







        When SQLite operation fails, the module should log error






        and continue without crashing.
        """

        # Try to connect to a path with permission issues (use a read-only location)

        # On Windows, we'll use a path that requires admin privileges
        import platform

        if platform.system() == "Windows":

            # Use a system directory that requires admin access

            invalid_path = "C:\\Windows\\System32\\test_database.db"

        else:

            # On Unix, use /root which requires root access

            invalid_path = "/root/test_database.db"

        # Attempt connection (should raise DatabaseError due to permissions)

        with pytest.raises(DatabaseError) as exc_info:

            sqlite_manager.connect_db(invalid_path)

        # Verify exception contains details

        assert "database" in str(exc_info.value).lower()

    def test_sqlite_insert_failure_logs_and_continues(self):
        """






        Validates: Requirement 4.4







        When SQLite insert operation fails, system should log error






        and continue without crashing.
        """

        # Create temporary database

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".db") as f:

            temp_db = f.name

        try:

            # Connect to database

            conn = sqlite_manager.connect_db(temp_db)

            # Create table

            sqlite_manager.crear_tabla(conn, "test_table")

            # Close connection to simulate failure

            conn.close()

            # Try to insert into closed connection (should raise DatabaseError)

            with pytest.raises(DatabaseError):

                sqlite_manager.insert_record(conn, "test_table", "2024-01-01", "12:00:00", 100.0)

        finally:

            # Cleanup

            if os.path.exists(temp_db):

                os.remove(temp_db)

    def test_sqlite_invalid_table_name_raises_error(self):
        """






        Validates: Requirement 4.4







        When SQLite operation uses invalid table name, system should
        raise appropriate error.
        """

        # Create temporary database

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".db") as f:

            temp_db = f.name

        try:

            # Connect to database

            conn = sqlite_manager.connect_db(temp_db)

            # Try to create table with invalid name (should raise DatabaseError)

            with pytest.raises(DatabaseError) as exc_info:

                sqlite_manager.crear_tabla(conn, "123invalid")  # Starts with number

            # Verify error message

            assert "Invalid table name" in str(exc_info.value)

            conn.close()

        finally:

            # Cleanup

            if os.path.exists(temp_db):

                os.remove(temp_db)

    @patch("modbuspython.backend.sqlite_manager.insertar_registro")
    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    def test_modbus_client_continues_when_sqlite_save_fails(self, mock_modbus_tcp_client, mock_insertar):
        """






        Validates: Requirement 4.4







        When SQLite save operation fails during Modbus read, the system






        should log error and continue reading without crashing.
        """

        # Setup mock

        mock_client_instance = MagicMock()

        mock_client_instance.connect.return_value = True

        # Mock successful read

        mock_response = MagicMock()

        mock_response.registers = [10000]

        mock_response.isError.return_value = False

        mock_client_instance.read_input_registers.return_value = mock_response

        mock_modbus_tcp_client.return_value = mock_client_instance

        # Mock SQLite insert to raise exception

        mock_insertar.side_effect = Exception("Database locked")

        # Create ModbusClient with minimal retry config

        from modbuspython.config.config_manager import ConfigurationManager

        config = ConfigurationManager()

        config._config = {
            "modbus": {"retry_attempts": 1, "retry_backoff": 0.01, "timeout": 5.0}  # Minimal retries for faster test
        }

        client = ModbusClient(ip="192.168.1.100", port=502, config_manager=config)

        client.connect()

        # Configure SQLite (with valid connection but insert will fail)

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".db") as f:

            temp_db = f.name

        try:

            conn = sqlite_manager.connect_db(temp_db)

            sqlite_manager.crear_tabla(conn, "test_table")

            # Set connection in client

            client.sqlite_conn = conn

            client.tabla_sqlite = "test_table"

            # Connect to signals

            radiation_spy = QSignalSpy(client.irradiance_updated)

            log_spy = QSignalSpy(client.log)

            # Read radiation (SQLite save will fail, but read should succeed)

            client.read_irradiance()

            # Verify radiation signal was emitted (read succeeded despite SQLite failure)

            assert len(radiation_spy) == 1, f"Expected 1 radiation signal, got {len(radiation_spy)}"

            assert radiation_spy[0][0] == pytest.approx(100.0)

            # Verify SQLite insert was attempted

            assert mock_insertar.called, "SQLite insert should have been attempted"

            # Verify error was logged for SQLite failure

            assert len(log_spy) > 0

            # Verify system continues operating

            assert client.is_connected is True

            # Cleanup connection before removing file

            conn.close()

        finally:

            # Cleanup - ensure connection is closed

            try:

                if "conn" in locals() and conn:

                    conn.close()

            except:
                pass

            # Remove file

            try:

                if os.path.exists(temp_db):

                    os.remove(temp_db)

            except PermissionError:

                # File might still be locked, ignore
                pass


class TestSystemContinuesOperating:
    """Test that system continues operating after various failures."""

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    def test_system_recovers_after_connection_failure(self, mock_modbus_tcp_client):
        """






        Verify that system can recover and reconnect after connection failure.
        """

        # Setup mock to fail first, succeed second

        mock_client_instance = MagicMock()

        mock_client_instance.connect.side_effect = [False, False, False, True]

        mock_modbus_tcp_client.return_value = mock_client_instance

        # Create ModbusClient

        from modbuspython.config.config_manager import ConfigurationManager

        config = ConfigurationManager()

        config._config = {"modbus": {"retry_attempts": 3, "retry_backoff": 0.1, "timeout": 5.0}}

        client = ModbusClient(ip="192.168.1.100", port=502, config_manager=config)

        # First connection attempt fails

        client.connect()

        assert client.is_connected is False

        assert client.is_in_safe_state() is True

        # Exit safe state manually

        client.exit_safe_state()

        assert client.is_in_safe_state() is False

        # Second connection attempt succeeds

        client.connect()

        assert client.is_connected is True

        assert client.is_in_safe_state() is False

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    def test_multiple_read_failures_do_not_crash_system(self, mock_modbus_tcp_client):
        """






        Verify that multiple consecutive read failures don't crash the system.
        """

        # Setup mock

        mock_client_instance = MagicMock()

        mock_client_instance.connect.return_value = True

        mock_client_instance.read_input_registers.side_effect = Exception("Persistent error")

        mock_modbus_tcp_client.return_value = mock_client_instance

        # Create ModbusClient

        from modbuspython.config.config_manager import ConfigurationManager

        config = ConfigurationManager()

        config._config = {"modbus": {"retry_attempts": 2, "retry_backoff": 0.1, "timeout": 5.0}}

        client = ModbusClient(ip="192.168.1.100", port=502, config_manager=config)

        client.connect()

        # Perform multiple read attempts (should not crash)

        for _ in range(5):

            client.read_irradiance()

        # Verify system is still operational (no crash)

        assert client is not None


class TestLoggingDuringFailures:
    """Test that appropriate logging occurs during failures."""

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    def test_connection_failure_emits_log_signals(self, mock_modbus_tcp_client):
        """






        Verify that connection failures emit appropriate log signals.
        """

        # Setup mock to fail

        mock_client_instance = MagicMock()

        mock_client_instance.connect.return_value = False

        mock_modbus_tcp_client.return_value = mock_client_instance

        # Create ModbusClient

        client = ModbusClient(ip="192.168.1.100", port=502)

        # Connect to log signal

        log_spy = QSignalSpy(client.log)

        # Attempt connection

        client.connect()

        # Verify log signals were emitted

        assert len(log_spy) > 0

        # Verify log contains connection attempt information

        log_messages = [signal[0] for signal in log_spy]

        assert any("Intentando conectar" in msg or "DEBUG" in msg for msg in log_messages)

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    def test_read_failure_emits_log_signals(self, mock_modbus_tcp_client):
        """






        Verify that read failures emit appropriate log signals.
        """

        # Setup mock

        mock_client_instance = MagicMock()

        mock_client_instance.connect.return_value = True

        mock_client_instance.read_input_registers.side_effect = Exception("Read error")

        mock_modbus_tcp_client.return_value = mock_client_instance

        # Create ModbusClient

        client = ModbusClient(ip="192.168.1.100", port=502)

        client.connect()

        # Connect to log signal

        log_spy = QSignalSpy(client.log)

        # Attempt read

        client.read_irradiance()

        # Verify log signals were emitted

        assert len(log_spy) > 0

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    def test_write_failure_emits_log_signals(self, mock_modbus_tcp_client):
        """






        Verify that write failures emit appropriate log signals.
        """

        # Setup mock

        mock_client_instance = MagicMock()

        mock_client_instance.connect.return_value = True

        mock_client_instance.write_register.side_effect = Exception("Write error")

        mock_modbus_tcp_client.return_value = mock_client_instance

        # Create ModbusClient

        client = ModbusClient(ip="192.168.1.100", port=502)

        client.connect()

        # Connect to log signal

        log_spy = QSignalSpy(client.log)

        # Attempt write

        client.write_setpoints(90, 45)

        # Verify log signals were emitted

        assert len(log_spy) > 0
