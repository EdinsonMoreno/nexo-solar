"""Unit tests for error handling across the application.




Tests cover:



- Modbus connection errors



- Modbus read/write operation errors



- Database operation errors



- Configuration errors



- System continues operating after errors



- Appropriate logging of errors




Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.8
"""

import pytest


import sqlite3


from pathlib import Path


from unittest.mock import Mock, patch, MagicMock


import sys

# Add parent directory to path to allow imports


sys.path.insert(0, str(Path(__file__).parent.parent.parent))


from modbuspython.exceptions import ModbusConnectionError, ModbusOperationError, DatabaseError, ConfigurationError


from modbuspython.config.config_manager import ConfigurationManager


from modbuspython.data_access.modbus_client import ModbusClient


from modbuspython.backend import sqlite_manager


class TestModbusConnectionErrors:
    """Test Modbus connection error handling (Requirement 4.1)."""

    @pytest.fixture
    def mock_config_manager(self):
        """Create a mock configuration manager."""

        config = Mock()

        config.get = Mock(
            side_effect=lambda key, default=None: {
                "modbus.retry_attempts": 1,  # Reduce retries for faster tests
                "modbus.retry_backoff": 0.1,
                "modbus.timeout": 1.0,
            }.get(key, default)
        )
        return config

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    def test_connection_failure_logs_error(self, mock_client_class, mock_config_manager):
        """Test that connection failures are handled appropriately."""

        # Setup mock to fail connection

        mock_client = Mock()

        mock_client.connect.return_value = False

        mock_client_class.return_value = mock_client

        # Create ModbusClient and attempt connection

        client = ModbusClient(ip="192.168.1.100", port=502, config_manager=mock_config_manager)

        client.connect()

        # Verify connection failed
        assert not client.is_connected

        # Verify system entered safe state after connection failure
        assert client.safe_state

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    def test_connection_timeout_handled_gracefully(self, mock_client_class, mock_config_manager):
        """Test that connection timeouts are handled without crashing."""

        # Setup mock to raise timeout exception

        mock_client = Mock()

        mock_client.connect.side_effect = OSError("Connection timed out")

        mock_client_class.return_value = mock_client

        # Create ModbusClient and attempt connection

        client = ModbusClient(ip="192.168.1.100", port=502, config_manager=mock_config_manager)

        # Should not raise exception - error is handled internally

        client.connect()

        # Verify system continues operating
        assert not client.is_connected

        assert client.safe_state  # Should enter safe state

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    def test_connection_retry_exhausted_emits_signal(self, mock_client_class, mock_config_manager):
        """Test that retry exhaustion emits appropriate signal."""

        # Setup mock to always fail

        mock_client = Mock()

        mock_client.connect.return_value = False

        mock_client_class.return_value = mock_client

        # Create ModbusClient

        client = ModbusClient(ip="192.168.1.100", port=502, config_manager=mock_config_manager)

        # Connect signal handler

        signal_emitted = []

        client.retry_exhausted.connect(lambda op, msg: signal_emitted.append((op, msg)))

        # Attempt connection

        client.connect()

        # Verify signal was emitted

        assert len(signal_emitted) == 1

        assert signal_emitted[0][0] == "Connection"

        assert "Failed to establish Modbus connection" in signal_emitted[0][1]


class TestModbusOperationErrors:
    """Test Modbus read/write operation error handling (Requirements 4.2, 4.3)."""

    @pytest.fixture
    def connected_client(self, mock_config_manager):
        """Create a connected ModbusClient for testing."""

        with patch("modbuspython.data_access.modbus_client.ModbusTcpClient") as mock_client_class:

            mock_client = Mock()

            mock_client.connect.return_value = True

            mock_client_class.return_value = mock_client

            client = ModbusClient(ip="192.168.1.100", port=502, config_manager=mock_config_manager)

            client.connect()

            # Inject the mock client for test manipulation

            client.client = mock_client

            yield client

    @pytest.fixture
    def mock_config_manager(self):
        """Create a mock configuration manager."""

        config = Mock()

        config.get = Mock(
            side_effect=lambda key, default=None: {
                "modbus.retry_attempts": 1,
                "modbus.retry_backoff": 0.1,
                "modbus.timeout": 1.0,
            }.get(key, default)
        )
        return config

    def test_read_error_logs_and_continues(self, connected_client):
        """Test that read errors are handled and system continues operating."""

        # Setup mock to return error response

        mock_response = Mock()

        mock_response.isError.return_value = True

        connected_client.client.read_input_registers.return_value = mock_response

        # Attempt read

        connected_client.leer_radiacion()

        # Verify system continues (doesn't crash) - connection marked as failed
        assert not connected_client.is_connected

    def test_write_error_enters_safe_state(self, connected_client):
        """Test that write errors cause system to enter safe state."""

        # Setup mock to return error response

        mock_response = Mock()

        mock_response.isError.return_value = True

        connected_client.client.write_register.return_value = mock_response

        # Attempt write

        connected_client.escribir_consignas(90, 45)

        # Verify system entered safe state
        assert connected_client.safe_state

    def test_safe_state_prevents_further_writes(self, connected_client):
        """Test that safe state prevents further write operations."""

        # Put system in safe state

        connected_client.safe_state = True

        # Mock write_register to track calls

        connected_client.client.write_register = Mock()

        # Attempt write

        connected_client.escribir_consignas(90, 45)

        # Verify write was not attempted

        connected_client.client.write_register.assert_not_called()

    def test_read_allows_operation_after_write_error(self, connected_client):
        """Test that read operations continue after write errors."""

        # Cause write error to enter safe state

        mock_response = Mock()

        mock_response.isError.return_value = True

        connected_client.client.write_register.return_value = mock_response

        connected_client.escribir_consignas(90, 45)

        # Verify in safe state
        assert connected_client.safe_state

        # Setup successful read

        mock_read_response = Mock()

        mock_read_response.isError.return_value = False

        mock_read_response.registers = [12345]

        connected_client.client.read_input_registers.return_value = mock_read_response

        connected_client.is_connected = True  # Reset connection state

        # Attempt read - should work

        signal_emitted = []

        connected_client.radiacion_actualizada.connect(lambda val: signal_emitted.append(val))

        connected_client.leer_radiacion()

        # Verify read succeeded

        assert len(signal_emitted) == 1


class TestDatabaseErrors:
    """Test database error handling (Requirement 4.4)."""

    def test_connection_error_raises_database_error(self, tmp_path):
        """Test that database connection errors raise DatabaseError."""

        # Try to connect with permission denied by using a read-only file

        db_path = tmp_path / "readonly.db"

        # Create a file and make it read-only

        db_path.touch()
        import os

        os.chmod(db_path, 0o444)  # Read-only

        try:

            # Try to connect and write (should fail on read-only file)

            conn = sqlite_manager.conectar_db(str(db_path))

            # Try to create a table (this should fail on read-only database)

            with pytest.raises(DatabaseError) as exc_info:

                sqlite_manager.crear_tabla(conn, "test_table")

            # Verify error details

            assert "Failed to create table" in str(exc_info.value)

            assert exc_info.value.details is not None

            conn.close()

        finally:

            # Restore permissions for cleanup

            os.chmod(db_path, 0o666)

    def test_invalid_table_name_raises_database_error(self, tmp_path):
        """Test that invalid table names raise DatabaseError."""

        # Create valid connection

        db_path = tmp_path / "test.db"

        conn = sqlite_manager.conectar_db(str(db_path))

        # Try to create table with invalid name

        with pytest.raises(DatabaseError) as exc_info:

            sqlite_manager.crear_tabla(conn, "123invalid")  # Starts with number

        # Verify error details

        assert "Invalid table name" in str(exc_info.value)

        conn.close()

    def test_insert_error_logs_and_raises(self, tmp_path):
        """Test that insert errors are raised as DatabaseError."""

        # Create valid connection and table

        db_path = tmp_path / "test.db"

        conn = sqlite_manager.conectar_db(str(db_path))

        sqlite_manager.crear_tabla(conn, "test_table")

        # Close connection to cause error

        conn.close()

        # Try to insert into closed connection - should raise DatabaseError

        with pytest.raises(DatabaseError) as exc_info:

            sqlite_manager.insert_record(conn, "test_table", "2024-01-01", "12:00:00", 500.0)

        # Verify error has details

        assert exc_info.value.details is not None

        assert "table_name" in exc_info.value.details

    def test_database_error_allows_application_to_continue(self, tmp_path):
        """Test that database errors don't crash the application."""

        # Create connection

        db_path = tmp_path / "test.db"

        conn = sqlite_manager.conectar_db(str(db_path))

        # Try to get tables from closed connection

        conn.close()

        # Should return empty list, not crash

        tables = sqlite_manager.get_tables(conn)

        assert tables == []


class TestConfigurationErrors:
    """Test configuration error handling (Requirement 4.5)."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton instance before each test."""

        ConfigurationManager._instance = None

        yield

        ConfigurationManager._instance = None

    @pytest.fixture
    def schema_path(self, tmp_path):
        """Create a temporary schema file for testing."""

        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": ["modbus"],
            "properties": {
                "modbus": {
                    "type": "object",
                    "required": ["host", "port"],
                    "properties": {"host": {"type": "string"}, "port": {"type": "integer"}},
                }
            },
        }

        schema_file = tmp_path / "test_schema.json"

        with open(schema_file, "w", encoding="utf-8") as f:

            import json

            json.dump(schema, f)

        return schema_file

    def test_missing_config_file_creates_default(self, tmp_path, schema_path, caplog):
        """Test that missing config file creates default configuration."""

        config_path = tmp_path / "missing_config.yaml"

        config_manager = ConfigurationManager()

        config_manager.load_config(config_path, schema_path)

        # Verify default config was loaded

        assert config_manager.get("modbus.host") is not None

        # Verify warning was logged

        assert any(
            "Configuration file not found" in record.message for record in caplog.records if record.levelname == "WARNING"
        )

    def test_invalid_yaml_falls_back_to_defaults(self, tmp_path, schema_path, caplog):
        """Test that invalid YAML falls back to default configuration."""

        config_path = tmp_path / "invalid.yaml"

        # Write invalid YAML

        with open(config_path, "w") as f:

            f.write("invalid: yaml: content: [unclosed")

        config_manager = ConfigurationManager()

        config_manager.load_config(config_path, schema_path)

        # Verify default config was loaded

        assert config_manager.get("modbus.host") is not None

        # Verify error was logged

        assert any("Failed to parse YAML" in record.message for record in caplog.records if record.levelname == "ERROR")

    def test_schema_validation_failure_falls_back(self, tmp_path, schema_path, caplog):
        """Test that schema validation failures fall back to defaults."""

        config_path = tmp_path / "invalid_schema.yaml"

        # Write config that doesn't match schema

        import yaml

        with open(config_path, "w") as f:

            yaml.dump({"modbus": {"host": "192.168.1.100"}}, f)  # Missing required 'port'

        config_manager = ConfigurationManager()

        config_manager.load_config(config_path, schema_path)

        # Verify default config was loaded

        assert config_manager.get("modbus.port") is not None

        # Verify error was logged

        assert any("schema validation failed" in record.message for record in caplog.records if record.levelname == "ERROR")

    def test_missing_schema_raises_configuration_error(self, tmp_path):
        """Test that missing schema file raises ConfigurationError."""

        config_path = tmp_path / "config.yaml"

        schema_path = tmp_path / "missing_schema.json"

        config_manager = ConfigurationManager()

        with pytest.raises(ConfigurationError) as exc_info:

            config_manager.load_config(config_path, schema_path)

        assert "Schema file not found" in str(exc_info.value)


class TestSystemContinuesOperating:
    """Test that system continues operating after errors (Requirement 4.8)."""

    @pytest.fixture
    def mock_config_manager(self):
        """Create a mock configuration manager."""

        config = Mock()

        config.get = Mock(
            side_effect=lambda key, default=None: {
                "modbus.retry_attempts": 1,
                "modbus.retry_backoff": 0.1,
                "modbus.timeout": 1.0,
            }.get(key, default)
        )
        return config

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    def test_modbus_error_allows_reconnection(self, mock_client_class, mock_config_manager):
        """Test that after Modbus error, reconnection is possible."""

        # Setup mock to fail first, succeed second

        mock_client = Mock()

        call_count = [0]

        def connect_side_effect():

            call_count[0] += 1

            return call_count[0] > 1  # Fail first, succeed second

        mock_client.connect.side_effect = connect_side_effect

        mock_client_class.return_value = mock_client

        # Create client and fail first connection

        client = ModbusClient(ip="192.168.1.100", port=502, config_manager=mock_config_manager)

        client.connect()
        assert not client.is_connected

        # Try to reconnect - should succeed

        client.connect()
        assert client.is_connected

    def test_database_error_allows_retry(self, tmp_path):
        """Test that after database error, operations can be retried."""

        # Create connection

        db_path = tmp_path / "test.db"

        conn = sqlite_manager.conectar_db(str(db_path))

        sqlite_manager.crear_tabla(conn, "test_table")

        # Cause error by trying invalid insert

        try:

            sqlite_manager.insert_record(conn, "nonexistent_table", "2024-01-01", "12:00:00", 500.0)

        except DatabaseError:

            pass  # Expected

        # Verify we can still use the connection

        tables = sqlite_manager.get_tables(conn)

        assert "test_table" in tables

        # Verify we can insert successfully

        sqlite_manager.insert_record(conn, "test_table", "2024-01-01", "12:00:00", 500.0)

        conn.close()


class TestLoggingOfErrors:
    """Test that errors are logged appropriately (Requirement 4.8)."""

    def test_modbus_errors_include_stack_trace(self):
        """Test that Modbus errors are handled with proper exception details."""

        from pymodbus.exceptions import ConnectionException

        with patch("modbuspython.data_access.modbus_client.ModbusTcpClient") as mock_client_class:

            mock_client = Mock()

            mock_client.connect.side_effect = ConnectionException("Test error")

            mock_client_class.return_value = mock_client

            config = Mock()

            config.get = Mock(
                side_effect=lambda key, default=None: {
                    "modbus.retry_attempts": 1,
                    "modbus.retry_backoff": 0.1,
                    "modbus.timeout": 1.0,
                }.get(key, default)
            )

            client = ModbusClient(ip="192.168.1.100", port=502, config_manager=config)

            client.connect()

            # Verify error was handled - system should be in safe state
            assert client.safe_state
            assert not client.is_connected

    def test_database_errors_include_context(self, tmp_path):
        """Test that database errors include contextual information in exception details."""

        db_path = tmp_path / "test.db"

        conn = sqlite_manager.conectar_db(str(db_path))

        # Try to create table with invalid name

        with pytest.raises(DatabaseError) as exc_info:

            sqlite_manager.crear_tabla(conn, "123invalid")

        # Verify error includes context in details

        assert exc_info.value.details is not None

        assert "table_name" in exc_info.value.details

        assert exc_info.value.details["table_name"] == "123invalid"

        conn.close()

    def test_configuration_errors_include_file_path(self, tmp_path, caplog):
        """Test that configuration errors log file paths."""

        ConfigurationManager._instance = None

        schema_path = tmp_path / "missing_schema.json"

        config_path = tmp_path / "config.yaml"

        config_manager = ConfigurationManager()

        try:

            config_manager.load_config(config_path, schema_path)

        except ConfigurationError:
            pass

        # Verify file path was logged

        assert any(str(schema_path) in record.message for record in caplog.records if record.levelname == "ERROR")
