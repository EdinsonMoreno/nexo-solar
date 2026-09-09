"""









Unit tests for ModbusClient.










Tests the ModbusClient class with all external dependencies mocked:









- pymodbus ModbusTcpClient









- QThread functionality









- PyQt6 signals









- SQLite database operations









- AngleStateManager









- RetryStrategy









- LoggingService










**Validates: Requirements 8.1, 8.8**
"""

import pytest


from unittest.mock import Mock, MagicMock, patch, call


from PyQt6.QtCore import QTimer


from PyQt6.QtTest import QSignalSpy


from modbuspython.data_access.modbus_client import ModbusClient


from modbuspython.exceptions import ModbusConnectionError, ModbusOperationError


class TestModbusClientInitialization:
    """Test ModbusClient initialization and configuration."""

    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_initialization_with_defaults(self, mock_logging, mock_angle_manager):
        """Test ModbusClient initializes with default parameters."""

        client = ModbusClient()

        assert client.ip == "192.168.1.100"

        assert client.port == 502

        assert client.is_connected is False

        assert client.is_running is False

        assert client.safe_state is False

        assert client.reg_radiacion == 0

        assert client.reg_motor1 == 1

        assert client.reg_motor2 == 2

        assert client.slave_id == 1

        assert client.sqlite_conn is None

        assert client.tabla_sqlite is None

        assert client.intervalo_lectura == 1000

    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_initialization_with_custom_parameters(self, mock_logging, mock_angle_manager):
        """Test ModbusClient initializes with custom parameters."""

        client = ModbusClient(ip="10.0.0.1", port=5020)

        assert client.ip == "10.0.0.1"

        assert client.port == 5020

    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_initialization_with_config_manager(self, mock_logging, mock_angle_manager):
        """Test ModbusClient initializes with ConfigurationManager."""

        mock_config = Mock()

        mock_config.get.side_effect = lambda key, default: {
            "modbus.retry_attempts": 5,
            "modbus.retry_backoff": 2.0,
            "modbus.timeout": 10.0,
        }.get(key, default)

        client = ModbusClient(config_manager=mock_config)

        assert client.retry_strategy.max_attempts == 5

        assert client.retry_strategy.initial_delay == 2.0

        assert client.timeout == 10.0

    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_initialization_connects_angle_manager_signal(self, mock_logging, mock_angle_manager):
        """Test that AngleStateManager signal is connected during initialization."""

        mock_angle_instance = Mock()

        mock_angle_manager.return_value = mock_angle_instance

        client = ModbusClient()

        mock_angle_instance.angles_changed.connect.assert_called_once()

    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_initialization_handles_angle_manager_failure(self, mock_logging, mock_angle_manager):
        """Test that initialization continues if AngleStateManager fails."""

        mock_angle_manager.side_effect = Exception("AngleStateManager error")

        client = ModbusClient()

        assert client.angle_manager is None


class TestModbusClientConnection:
    """Test ModbusClient connection methods."""

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_conectar_successful(self, mock_logging, mock_angle_manager, mock_modbus_tcp):
        """Test successful connection to Modbus server."""

        mock_client_instance = Mock()

        mock_client_instance.connect.return_value = True

        mock_modbus_tcp.return_value = mock_client_instance

        client = ModbusClient(ip="192.168.1.100", port=502)

        connection_spy = QSignalSpy(client.conexion_cambiada)

        client.connect()

        assert client.is_connected is True

        assert client.safe_state is False

        mock_modbus_tcp.assert_called_once_with("192.168.1.100", port=502, timeout=5.0)

        mock_client_instance.connect.assert_called_once()

        assert len(connection_spy) == 1

        assert connection_spy[0][0] is True

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_conectar_failed(self, mock_logging, mock_angle_manager, mock_modbus_tcp):
        """Test failed connection to Modbus server."""

        mock_client_instance = Mock()

        mock_client_instance.connect.return_value = False

        mock_modbus_tcp.return_value = mock_client_instance

        client = ModbusClient()

        connection_spy = QSignalSpy(client.conexion_cambiada)

        retry_spy = QSignalSpy(client.retry_exhausted)

        client.connect()

        assert client.is_connected is False

        assert client.safe_state is True

        assert len(connection_spy) == 1

        assert connection_spy[0][0] is False

        assert len(retry_spy) == 1

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_conectar_with_connection_exception(self, mock_logging, mock_angle_manager, mock_modbus_tcp):
        """Test connection with ConnectionException."""

        from pymodbus.exceptions import ConnectionException

        mock_client_instance = Mock()

        mock_client_instance.connect.side_effect = ConnectionException("Connection refused")

        mock_modbus_tcp.return_value = mock_client_instance

        client = ModbusClient()

        connection_spy = QSignalSpy(client.conexion_cambiada)

        client.connect()

        assert client.is_connected is False

        assert client.safe_state is True

        assert len(connection_spy) == 1

        assert connection_spy[0][0] is False

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_desconectar(self, mock_logging, mock_angle_manager, mock_modbus_tcp):
        """Test disconnection from Modbus server."""

        mock_client_instance = Mock()

        mock_client_instance.connect.return_value = True

        mock_modbus_tcp.return_value = mock_client_instance

        client = ModbusClient()

        client.connect()

        connection_spy = QSignalSpy(client.conexion_cambiada)

        client.disconnect()

        assert client.is_connected is False

        mock_client_instance.close.assert_called_once()

        assert len(connection_spy) == 1

        assert connection_spy[0][0] is False


class TestModbusClientReadOperations:
    """Test ModbusClient read operations."""

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_leer_radiacion_successful(self, mock_logging, mock_angle_manager, mock_modbus_tcp):
        """Test successful radiation reading."""

        mock_client_instance = Mock()

        mock_client_instance.connect.return_value = True

        mock_response = Mock()

        mock_response.registers = [12345]

        mock_response.isError.return_value = False

        mock_client_instance.read_input_registers.return_value = mock_response

        mock_modbus_tcp.return_value = mock_client_instance

        client = ModbusClient()

        client.connect()

        radiation_spy = QSignalSpy(client.irradiance_updated)

        client.read_irradiance()

        mock_client_instance.read_input_registers.assert_called_once_with(address=0, count=1)

        assert len(radiation_spy) == 1

        assert radiation_spy[0][0] == pytest.approx(123.45)

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_leer_radiacion_when_not_connected(self, mock_logging, mock_angle_manager, mock_modbus_tcp):
        """Test reading radiation when not connected."""

        client = ModbusClient()

        radiation_spy = QSignalSpy(client.irradiance_updated)

        client.read_irradiance()

        assert len(radiation_spy) == 0

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_leer_radiacion_with_error_response(self, mock_logging, mock_angle_manager, mock_modbus_tcp):
        """Test reading radiation with error response."""

        mock_client_instance = Mock()

        mock_client_instance.connect.return_value = True

        mock_response = Mock()

        mock_response.isError.return_value = True

        mock_client_instance.read_input_registers.return_value = mock_response

        mock_modbus_tcp.return_value = mock_client_instance

        client = ModbusClient()

        client.connect()

        radiation_spy = QSignalSpy(client.irradiance_updated)

        retry_spy = QSignalSpy(client.retry_exhausted)

        client.read_irradiance()

        assert len(radiation_spy) == 0

        assert client.is_connected is False

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_leer_radiacion_with_none_response(self, mock_logging, mock_angle_manager, mock_modbus_tcp):
        """Test reading radiation with None response."""

        mock_client_instance = Mock()

        mock_client_instance.connect.return_value = True

        mock_client_instance.read_input_registers.return_value = None

        mock_modbus_tcp.return_value = mock_client_instance

        client = ModbusClient()

        client.connect()

        radiation_spy = QSignalSpy(client.irradiance_updated)

        client.read_irradiance()

        assert len(radiation_spy) == 0

        assert client.is_connected is False


class TestModbusClientWriteOperations:
    """Test ModbusClient write operations."""

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_escribir_consignas_successful(self, mock_logging, mock_angle_manager, mock_modbus_tcp):
        """Test successful writing of setpoints."""

        mock_client_instance = Mock()

        mock_client_instance.connect.return_value = True

        mock_response = Mock()

        mock_response.isError.return_value = False

        mock_client_instance.write_register.return_value = mock_response

        mock_modbus_tcp.return_value = mock_client_instance

        client = ModbusClient()

        client.connect()

        client.write_setpoints(90, 45)

        assert mock_client_instance.write_register.call_count == 2

        mock_client_instance.write_register.assert_any_call(address=1, value=90)

        mock_client_instance.write_register.assert_any_call(address=2, value=45)

        assert client.safe_state is False

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_escribir_consignas_when_not_connected(self, mock_logging, mock_angle_manager, mock_modbus_tcp):
        """Test writing setpoints when not connected."""

        client = ModbusClient()

        client.write_setpoints(90, 45)

        # Should not raise exception, just log warning

        assert client.safe_state is False

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_escribir_consignas_in_safe_state(self, mock_logging, mock_angle_manager, mock_modbus_tcp):
        """Test writing setpoints when in safe state."""

        mock_client_instance = Mock()

        mock_client_instance.connect.return_value = True

        mock_modbus_tcp.return_value = mock_client_instance

        client = ModbusClient()

        client.connect()

        client.safe_state = True

        client.write_setpoints(90, 45)

        # Should not attempt write when in safe state

        mock_client_instance.write_register.assert_not_called()

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_escribir_consignas_with_error_response(self, mock_logging, mock_angle_manager, mock_modbus_tcp):
        """Test writing setpoints with error response."""

        mock_client_instance = Mock()

        mock_client_instance.connect.return_value = True

        mock_response = Mock()

        mock_response.isError.return_value = True

        mock_client_instance.write_register.return_value = mock_response

        mock_modbus_tcp.return_value = mock_client_instance

        client = ModbusClient()

        client.connect()

        retry_spy = QSignalSpy(client.retry_exhausted)

        client.write_setpoints(90, 45)

        assert client.safe_state is True

        assert len(retry_spy) == 1


class TestModbusClientValidation:
    """Test ModbusClient validation methods."""

    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_validate_angles_within_range(self, mock_logging, mock_angle_manager):
        """Test angle validation with values within valid range."""

        client = ModbusClient()

        rot, ele = client._validate_angles(180, 90)

        assert rot == 180

        assert ele == 90

    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_validate_angles_clamps_rotation(self, mock_logging, mock_angle_manager):
        """Test angle validation clamps rotation to 0-360."""

        client = ModbusClient()

        rot_low, _ = client._validate_angles(-10, 90)

        rot_high, _ = client._validate_angles(400, 90)

        assert rot_low == 0

        assert rot_high == 360

    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_validate_angles_clamps_elevation(self, mock_logging, mock_angle_manager):
        """Test angle validation clamps elevation to 0-145."""

        client = ModbusClient()

        _, ele_low = client._validate_angles(180, -10)

        _, ele_high = client._validate_angles(180, 200)

        assert ele_low == 0

        assert ele_high == 145

    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_validate_angles_handles_float_values(self, mock_logging, mock_angle_manager):
        """Test angle validation rounds float values."""

        client = ModbusClient()

        rot, ele = client._validate_angles(180.7, 90.3)

        assert rot == 181

        assert ele == 90

    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_validate_angles_handles_invalid_input(self, mock_logging, mock_angle_manager):
        """Test angle validation handles invalid input gracefully."""

        client = ModbusClient()

        rot, ele = client._validate_angles("invalid", None)

        assert rot == 0

        assert ele == 0


class TestModbusClientSafeState:
    """Test ModbusClient safe state functionality."""

    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_is_in_safe_state(self, mock_logging, mock_angle_manager):
        """Test checking if system is in safe state."""

        client = ModbusClient()

        assert client.is_in_safe_state() is False

        client.safe_state = True

        assert client.is_in_safe_state() is True

    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_exit_safe_state(self, mock_logging, mock_angle_manager):
        """Test exiting safe state."""

        client = ModbusClient()

        client.safe_state = True

        client.exit_safe_state()

        assert client.safe_state is False

    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_exit_safe_state_when_not_in_safe_state(self, mock_logging, mock_angle_manager):
        """Test exiting safe state when not in safe state."""

        client = ModbusClient()

        client.exit_safe_state()

        assert client.safe_state is False

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_safe_state_set_on_connection_failure(self, mock_logging, mock_angle_manager, mock_modbus_tcp):
        """Test that safe state is set when connection fails."""

        mock_client_instance = Mock()

        mock_client_instance.connect.return_value = False

        mock_modbus_tcp.return_value = mock_client_instance

        client = ModbusClient()

        client.connect()

        assert client.safe_state is True

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_safe_state_cleared_on_successful_connection(self, mock_logging, mock_angle_manager, mock_modbus_tcp):
        """Test that safe state is cleared on successful connection."""

        mock_client_instance = Mock()

        mock_client_instance.connect.return_value = True

        mock_modbus_tcp.return_value = mock_client_instance

        client = ModbusClient()

        client.safe_state = True

        client.connect()

        assert client.safe_state is False


class TestModbusClientSQLiteIntegration:
    """Test ModbusClient SQLite integration."""

    @patch("modbuspython.data_access.modbus_client.sqlite_manager")
    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_configurar_sqlite_successful(self, mock_logging, mock_angle_manager, mock_sqlite):
        """Test successful SQLite configuration."""

        mock_conn = Mock()

        mock_sqlite.conectar_db.return_value = mock_conn

        mock_sqlite.obtener_tablas.return_value = ["existing_table"]

        client = ModbusClient()

        result = client.configure_sqlite("/path/to/db.sqlite", "test_table")

        assert result is True

        assert client.sqlite_conn == mock_conn

        assert client.tabla_sqlite == "test_table"

        mock_sqlite.crear_tabla.assert_called_once_with(mock_conn, "test_table")

    @patch("modbuspython.data_access.modbus_client.sqlite_manager")
    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_configurar_sqlite_table_exists(self, mock_logging, mock_angle_manager, mock_sqlite):
        """Test SQLite configuration when table already exists."""

        mock_conn = Mock()

        mock_sqlite.conectar_db.return_value = mock_conn

        mock_sqlite.obtener_tablas.return_value = ["test_table"]

        client = ModbusClient()

        result = client.configure_sqlite("/path/to/db.sqlite", "test_table")

        assert result is True

        mock_sqlite.crear_tabla.assert_not_called()

    @patch("modbuspython.data_access.modbus_client.sqlite_manager")
    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_configurar_sqlite_error(self, mock_logging, mock_angle_manager, mock_sqlite):
        """Test SQLite configuration with error."""

        mock_sqlite.conectar_db.side_effect = Exception("Database error")

        client = ModbusClient()

        result = client.configure_sqlite("/path/to/db.sqlite", "test_table")

        assert result is False

        assert client.sqlite_conn is None

        assert client.tabla_sqlite is None

    @patch("modbuspython.data_access.modbus_client.sqlite_manager")
    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_guardar_en_sqlite_successful(self, mock_logging, mock_angle_manager, mock_sqlite):
        """Test successful saving to SQLite."""

        mock_conn = Mock()

        mock_sqlite.conectar_db.return_value = mock_conn

        mock_sqlite.obtener_tablas.return_value = ["test_table"]

        client = ModbusClient()

        client.configure_sqlite("/path/to/db.sqlite", "test_table")

        client._save_to_sqlite(850.5)

        mock_sqlite.insertar_registro.assert_called_once()

        args = mock_sqlite.insertar_registro.call_args[0]

        assert args[0] == mock_conn

        assert args[1] == "test_table"

        assert args[4] == 850.5

    @patch("modbuspython.data_access.modbus_client.sqlite_manager")
    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_guardar_en_sqlite_when_not_configured(self, mock_logging, mock_angle_manager, mock_sqlite):
        """Test saving to SQLite when not configured."""

        client = ModbusClient()

        client._save_to_sqlite(850.5)

        mock_sqlite.insertar_registro.assert_not_called()

    @patch("modbuspython.data_access.modbus_client.sqlite_manager")
    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_guardar_en_sqlite_error_handling(self, mock_logging, mock_angle_manager, mock_sqlite):
        """Test error handling when saving to SQLite."""

        mock_conn = Mock()

        mock_sqlite.conectar_db.return_value = mock_conn

        mock_sqlite.obtener_tablas.return_value = ["test_table"]

        mock_sqlite.insertar_registro.side_effect = Exception("Insert error")

        client = ModbusClient()

        client.configure_sqlite("/path/to/db.sqlite", "test_table")

        # Should not raise exception

        client._save_to_sqlite(850.5)


class TestModbusClientAngleStateIntegration:
    """Test ModbusClient integration with AngleStateManager."""

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_on_angles_changed_in_auto_mode(self, mock_logging, mock_angle_manager, mock_modbus_tcp):
        """Test angle change handler in auto mode."""

        mock_angle_instance = Mock()

        mock_angle_instance.get_mode.return_value = "auto"

        mock_angle_manager.return_value = mock_angle_instance

        mock_client_instance = Mock()

        mock_client_instance.connect.return_value = True

        mock_response = Mock()

        mock_response.isError.return_value = False

        mock_client_instance.write_register.return_value = mock_response

        mock_modbus_tcp.return_value = mock_client_instance

        client = ModbusClient()

        client.connect()

        client._on_angles_changed(180, 90, source="auto")

        assert mock_client_instance.write_register.call_count == 2

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_on_angles_changed_in_manual_mode(self, mock_logging, mock_angle_manager, mock_modbus_tcp):
        """Test angle change handler in manual mode."""

        mock_angle_instance = Mock()

        mock_angle_instance.get_mode.return_value = "manual"

        mock_angle_manager.return_value = mock_angle_instance

        mock_client_instance = Mock()

        mock_client_instance.connect.return_value = True

        mock_response = Mock()

        mock_response.isError.return_value = False

        mock_client_instance.write_register.return_value = mock_response

        mock_modbus_tcp.return_value = mock_client_instance

        client = ModbusClient()

        client.connect()

        client._on_angles_changed(180, 90, source="manual")

        assert mock_client_instance.write_register.call_count == 2

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_on_angles_changed_from_prueba_source(self, mock_logging, mock_angle_manager, mock_modbus_tcp):
        """Test angle change handler ignores prueba source."""

        mock_angle_instance = Mock()

        mock_angle_instance.get_mode.return_value = "auto"

        mock_angle_manager.return_value = mock_angle_instance

        mock_client_instance = Mock()

        mock_client_instance.connect.return_value = True

        mock_modbus_tcp.return_value = mock_client_instance

        client = ModbusClient()

        client.connect()

        client._on_angles_changed(180, 90, source="prueba")

        mock_client_instance.write_register.assert_not_called()

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_on_angles_changed_when_not_connected(self, mock_logging, mock_angle_manager, mock_modbus_tcp):
        """Test angle change handler when not connected."""

        mock_angle_instance = Mock()

        mock_angle_instance.get_mode.return_value = "auto"

        mock_angle_manager.return_value = mock_angle_instance

        mock_client_instance = Mock()

        mock_modbus_tcp.return_value = mock_client_instance

        client = ModbusClient()

        client._on_angles_changed(180, 90, source="auto")

        mock_client_instance.write_register.assert_not_called()

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_on_angles_changed_validates_angles(self, mock_logging, mock_angle_manager, mock_modbus_tcp):
        """Test angle change handler validates and clamps angles."""

        mock_angle_instance = Mock()

        mock_angle_instance.get_mode.return_value = "auto"

        mock_angle_manager.return_value = mock_angle_instance

        mock_client_instance = Mock()

        mock_client_instance.connect.return_value = True

        mock_response = Mock()

        mock_response.isError.return_value = False

        mock_client_instance.write_register.return_value = mock_response

        mock_modbus_tcp.return_value = mock_client_instance

        client = ModbusClient()

        client.connect()

        client._on_angles_changed(400, 200, source="auto")

        # Should clamp to valid ranges

        calls = mock_client_instance.write_register.call_args_list

        assert calls[0][1]["value"] == 360  # Rotation clamped to 360

        assert calls[1][1]["value"] == 145  # Elevation clamped to 145


class TestModbusClientTimerOperations:
    """Test ModbusClient timer and periodic reading operations."""

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_iniciar_starts_timer_when_connected(self, mock_logging, mock_angle_manager, mock_modbus_tcp):
        """Test that iniciar starts timer when connected."""

        mock_client_instance = Mock()

        mock_client_instance.connect.return_value = True

        mock_modbus_tcp.return_value = mock_client_instance

        client = ModbusClient()

        client.connect()

        # Create a mock timer

        mock_timer = Mock()

        client.timer = mock_timer

        client.start(2000)

        mock_timer.start.assert_called_once_with(2000)

        assert client.intervalo_lectura == 2000

    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_iniciar_does_not_start_when_not_connected(self, mock_logging, mock_angle_manager):
        """Test that iniciar does not start timer when not connected."""

        client = ModbusClient()

        mock_timer = Mock()

        client.timer = mock_timer

        client.start(2000)

        mock_timer.start.assert_not_called()

    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_detener_lectura_stops_timer(self, mock_logging, mock_angle_manager):
        """Test that detener_lectura stops the timer."""

        client = ModbusClient()

        mock_timer = Mock()

        client.timer = mock_timer

        client.stop_reading()

        mock_timer.stop.assert_called_once()

    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_detener_lectura_handles_no_timer(self, mock_logging, mock_angle_manager):
        """Test that detener_lectura handles missing timer gracefully."""

        client = ModbusClient()

        client.timer = None

        # Should not raise exception

        client.stop_reading()


class TestModbusClientResourceCleanup:
    """Test ModbusClient resource cleanup and shutdown."""

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_stop_closes_modbus_connection(self, mock_logging, mock_angle_manager, mock_modbus_tcp):
        """Test that stop closes Modbus connection."""

        mock_client_instance = Mock()

        mock_client_instance.connect.return_value = True

        mock_modbus_tcp.return_value = mock_client_instance

        client = ModbusClient()

        client.connect()

        mock_timer = Mock()

        client.timer = mock_timer

        # Mock the wait method to return True immediately

        with patch.object(client, "wait", return_value=True):

            client.stop()

        mock_client_instance.close.assert_called_once()

        assert client.is_connected is False

        assert client.is_running is False

    @patch("modbuspython.data_access.modbus_client.sqlite_manager")
    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_stop_closes_sqlite_connection(self, mock_logging, mock_angle_manager, mock_modbus_tcp, mock_sqlite):
        """Test that stop closes SQLite connection."""

        mock_conn = Mock()

        mock_sqlite.conectar_db.return_value = mock_conn

        mock_sqlite.obtener_tablas.return_value = ["test_table"]

        client = ModbusClient()

        client.configure_sqlite("/path/to/db.sqlite", "test_table")

        mock_timer = Mock()

        client.timer = mock_timer

        with patch.object(client, "wait", return_value=True):

            client.stop()

        mock_conn.close.assert_called_once()

    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_stop_stops_timer(self, mock_logging, mock_angle_manager):
        """Test that stop stops the timer."""

        client = ModbusClient()

        mock_timer = Mock()

        client.timer = mock_timer

        with patch.object(client, "wait", return_value=True):

            client.stop()

        mock_timer.stop.assert_called_once()

    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_stop_handles_errors_gracefully(self, mock_logging, mock_angle_manager):
        """Test that stop handles errors during cleanup gracefully."""

        client = ModbusClient()

        mock_timer = Mock()

        mock_timer.stop.side_effect = Exception("Timer error")

        client.timer = mock_timer

        # Should not raise exception

        with patch.object(client, "wait", return_value=True):

            client.stop()

    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_stop_with_timeout(self, mock_logging, mock_angle_manager):
        """Test that stop handles thread timeout."""

        client = ModbusClient()

        mock_timer = Mock()

        client.timer = mock_timer

        # Mock wait to return False (timeout)

        with patch.object(client, "wait", return_value=False):

            with patch.object(client, "terminate") as mock_terminate:

                client.stop()

                mock_terminate.assert_called_once()


class TestModbusClientSignalEmissions:
    """Test ModbusClient signal emissions."""

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_log_signal_emission(self, mock_logging, mock_angle_manager, mock_modbus_tcp):
        """Test that log signal is emitted."""

        client = ModbusClient()

        log_spy = QSignalSpy(client.log)

        # Trigger an action that emits log signal

        client.read_irradiance()

        assert len(log_spy) > 0

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_retry_exhausted_signal_on_connection_failure(self, mock_logging, mock_angle_manager, mock_modbus_tcp):
        """Test that retry_exhausted signal is emitted on connection failure."""

        mock_client_instance = Mock()

        mock_client_instance.connect.return_value = False

        mock_modbus_tcp.return_value = mock_client_instance

        client = ModbusClient()

        retry_spy = QSignalSpy(client.retry_exhausted)

        client.connect()

        assert len(retry_spy) == 1

        assert retry_spy[0][0] == "Connection"

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_retry_exhausted_signal_on_write_failure(self, mock_logging, mock_angle_manager, mock_modbus_tcp):
        """Test that retry_exhausted signal is emitted on write failure."""

        mock_client_instance = Mock()

        mock_client_instance.connect.return_value = True

        mock_response = Mock()

        mock_response.isError.return_value = True

        mock_client_instance.write_register.return_value = mock_response

        mock_modbus_tcp.return_value = mock_client_instance

        client = ModbusClient()

        client.connect()

        retry_spy = QSignalSpy(client.retry_exhausted)

        client.write_setpoints(90, 45)

        assert len(retry_spy) == 1

        assert retry_spy[0][0] == "Write Setpoints"


class TestModbusClientEdgeCases:
    """Test ModbusClient edge cases and error scenarios."""

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_multiple_connect_calls(self, mock_logging, mock_angle_manager, mock_modbus_tcp):
        """Test multiple consecutive connect calls."""

        mock_client_instance = Mock()

        mock_client_instance.connect.return_value = True

        mock_modbus_tcp.return_value = mock_client_instance

        client = ModbusClient()

        client.connect()

        client.connect()

        # Should handle multiple connects gracefully

        assert client.is_connected is True

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_disconnect_when_not_connected(self, mock_logging, mock_angle_manager, mock_modbus_tcp):
        """Test disconnecting when not connected."""

        client = ModbusClient()

        # Should not raise exception

        client.disconnect()

        assert client.is_connected is False

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_read_with_empty_registers(self, mock_logging, mock_angle_manager, mock_modbus_tcp):
        """Test reading with empty registers in response."""

        mock_client_instance = Mock()

        mock_client_instance.connect.return_value = True

        mock_response = Mock()

        mock_response.registers = []

        mock_response.isError.return_value = False

        mock_client_instance.read_input_registers.return_value = mock_response

        mock_modbus_tcp.return_value = mock_client_instance

        client = ModbusClient()

        client.connect()

        radiation_spy = QSignalSpy(client.irradiance_updated)

        client.read_irradiance()

        # Should handle empty registers gracefully

        assert len(radiation_spy) == 0

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_write_with_none_response(self, mock_logging, mock_angle_manager, mock_modbus_tcp):
        """Test writing with None response."""

        mock_client_instance = Mock()

        mock_client_instance.connect.return_value = True

        mock_client_instance.write_register.return_value = None

        mock_modbus_tcp.return_value = mock_client_instance

        client = ModbusClient()

        client.connect()

        retry_spy = QSignalSpy(client.retry_exhausted)

        client.write_setpoints(90, 45)

        # Should handle None response and enter safe state

        assert client.safe_state is True

        assert len(retry_spy) == 1

    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_detener_is_alias_for_desconectar(self, mock_logging, mock_angle_manager):
        """Test that detener is an alias for desconectar."""

        client = ModbusClient()

        # Mock desconectar to verify it's called

        with patch.object(client, "desconectar") as mock_desconectar:

            client.stop_all()

            mock_desconectar.assert_called_once()

    @patch("modbuspython.data_access.modbus_client.sqlite_manager")
    @patch("modbuspython.data_access.modbus_client.AngleStateManager")
    @patch("modbuspython.data_access.modbus_client.LoggingService")
    def test_configurar_sqlite_closes_previous_connection(self, mock_logging, mock_angle_manager, mock_sqlite):
        """Test that configurar_sqlite closes previous connection."""

        mock_conn1 = Mock()

        mock_conn2 = Mock()

        mock_sqlite.conectar_db.side_effect = [mock_conn1, mock_conn2]

        mock_sqlite.obtener_tablas.return_value = ["test_table"]

        client = ModbusClient()

        client.configure_sqlite("/path/to/db1.sqlite", "table1")

        client.configure_sqlite("/path/to/db2.sqlite", "table2")

        # First connection should be closed

        mock_conn1.close.assert_called_once()

        assert client.sqlite_conn == mock_conn2
