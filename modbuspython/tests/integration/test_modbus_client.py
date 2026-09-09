"""Integration tests for ModbusClient.






Tests the ModbusClient class including connection, read/write operations,





timeout handling, signal emissions, and thread operation.






These tests use mocks for pymodbus to avoid requiring actual hardware.
"""

import sys


import pytest


from pathlib import Path


from unittest.mock import Mock, patch, MagicMock, call


from PyQt6.QtCore import QTimer, QEventLoop


from PyQt6.QtTest import QSignalSpy
import time

# Add parent directory to path for imports


sys.path.insert(0, str(Path(__file__).parent.parent.parent))


from modbuspython.data_access.modbus_client import ModbusClient


class TestModbusClientConnection:
    """Test ModbusClient connection functionality."""

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    def test_successful_connection(self, mock_modbus_tcp_client):
        """Test successful connection to Modbus server."""

        # Setup mock

        mock_client_instance = MagicMock()

        mock_client_instance.connect.return_value = True

        mock_modbus_tcp_client.return_value = mock_client_instance

        # Create ModbusClient

        client = ModbusClient(ip="192.168.1.100", port=502)

        # Connect to signal

        connection_spy = QSignalSpy(client.conexion_cambiada)

        # Attempt connection

        client.connect()

        # Verify connection was attempted (with timeout parameter)

        mock_modbus_tcp_client.assert_called_once_with("192.168.1.100", port=502, timeout=5.0)

        mock_client_instance.connect.assert_called_once()

        # Verify connection state

        assert client.is_connected is True

        # Verify signal was emitted

        assert len(connection_spy) == 1

        assert connection_spy[0][0] is True

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    def test_failed_connection(self, mock_modbus_tcp_client):
        """Test failed connection to Modbus server."""

        # Setup mock to fail connection

        mock_client_instance = MagicMock()

        mock_client_instance.connect.return_value = False

        mock_modbus_tcp_client.return_value = mock_client_instance

        # Create ModbusClient

        client = ModbusClient(ip="192.168.1.100", port=502)

        # Connect to signal

        connection_spy = QSignalSpy(client.conexion_cambiada)

        # Attempt connection

        client.connect()

        # Verify connection state

        assert client.is_connected is False

        # Verify signal was emitted with False

        assert len(connection_spy) == 1

        assert connection_spy[0][0] is False

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    def test_connection_exception_handling(self, mock_modbus_tcp_client):
        """Test that connection exceptions are handled gracefully."""

        # Setup mock to raise exception

        mock_modbus_tcp_client.side_effect = Exception("Network error")

        # Create ModbusClient

        client = ModbusClient(ip="192.168.1.100", port=502)

        # Connect to signal

        connection_spy = QSignalSpy(client.conexion_cambiada)

        # Attempt connection (should not raise exception)

        client.connect()

        # Verify connection state

        assert client.is_connected is False

        # Verify signal was emitted with False

        assert len(connection_spy) == 1

        assert connection_spy[0][0] is False

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    def test_disconnect(self, mock_modbus_tcp_client):
        """Test disconnection from Modbus server."""

        # Setup mock

        mock_client_instance = MagicMock()

        mock_client_instance.connect.return_value = True

        mock_modbus_tcp_client.return_value = mock_client_instance

        # Create and connect ModbusClient

        client = ModbusClient(ip="192.168.1.100", port=502)

        client.connect()

        # Verify connected

        assert client.is_connected is True

        # Connect to signal

        connection_spy = QSignalSpy(client.conexion_cambiada)

        # Disconnect

        client.disconnect()

        # Verify disconnection

        assert client.is_connected is False

        mock_client_instance.close.assert_called_once()

        # Verify signal was emitted

        assert len(connection_spy) == 1

        assert connection_spy[0][0] is False


class TestModbusClientReadOperations:
    """Test ModbusClient read operations."""

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    def test_successful_read_radiation(self, mock_modbus_tcp_client):
        """Test successful reading of radiation register."""

        # Setup mock

        mock_client_instance = MagicMock()

        mock_client_instance.connect.return_value = True

        # Mock read response with radiation value

        mock_response = MagicMock()

        mock_response.registers = [12345]  # Raw value (will be divided by 100)

        mock_client_instance.read_input_registers.return_value = mock_response

        mock_modbus_tcp_client.return_value = mock_client_instance

        # Create and connect ModbusClient

        client = ModbusClient(ip="192.168.1.100", port=502)

        client.connect()

        # Connect to signal

        radiation_spy = QSignalSpy(client.irradiance_updated)

        # Read radiation

        client.read_irradiance()

        # Verify read was attempted

        mock_client_instance.read_input_registers.assert_called_once_with(address=0, count=1)

        # Verify signal was emitted with correct value

        assert len(radiation_spy) == 1

        assert radiation_spy[0][0] == pytest.approx(123.45)  # 12345 / 100

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    def test_read_radiation_when_not_connected(self, mock_modbus_tcp_client):
        """Test that reading radiation when not connected does not emit signal."""

        # Create ModbusClient without connecting

        client = ModbusClient(ip="192.168.1.100", port=502)

        # Connect to signal

        radiation_spy = QSignalSpy(client.irradiance_updated)

        # Try to read radiation while not connected

        client.read_irradiance()

        # Verify no signal was emitted

        assert len(radiation_spy) == 0


class TestModbusClientRetryLogic:
    """Test ModbusClient retry logic integration."""

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    def test_connection_retry_success_on_second_attempt(self, mock_modbus_tcp_client):
        """Test that connection succeeds on second retry attempt."""

        # Setup mock to fail first time, succeed second time

        mock_client_instance = MagicMock()

        mock_client_instance.connect.side_effect = [False, True]

        mock_modbus_tcp_client.return_value = mock_client_instance

        # Create ModbusClient with retry configuration

        from modbuspython.config.config_manager import ConfigurationManager

        config = ConfigurationManager()

        config._config = {"modbus": {"retry_attempts": 3, "retry_backoff": 0.1, "timeout": 5.0}}  # Short delay for testing

        client = ModbusClient(ip="192.168.1.100", port=502, config_manager=config)

        # Connect to signal

        connection_spy = QSignalSpy(client.conexion_cambiada)

        # Attempt connection

        client.connect()

        # Verify connection was attempted twice

        assert mock_client_instance.connect.call_count == 2

        # Verify connection succeeded

        assert client.is_connected is True

        # Verify signal was emitted

        assert len(connection_spy) == 1

        assert connection_spy[0][0] is True

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    def test_connection_retry_exhausted(self, mock_modbus_tcp_client):
        """Test that connection fails after all retry attempts exhausted."""

        # Setup mock to always fail

        mock_client_instance = MagicMock()

        mock_client_instance.connect.return_value = False

        mock_modbus_tcp_client.return_value = mock_client_instance

        # Create ModbusClient with retry configuration

        from modbuspython.config.config_manager import ConfigurationManager

        config = ConfigurationManager()

        config._config = {"modbus": {"retry_attempts": 3, "retry_backoff": 0.1, "timeout": 5.0}}  # Short delay for testing

        client = ModbusClient(ip="192.168.1.100", port=502, config_manager=config)

        # Connect to signal

        connection_spy = QSignalSpy(client.conexion_cambiada)

        # Attempt connection

        client.connect()

        # Verify connection was attempted 3 times (max_attempts)

        assert mock_client_instance.connect.call_count == 3

        # Verify connection failed

        assert client.is_connected is False

        # Verify signal was emitted with False

        assert len(connection_spy) == 1

        assert connection_spy[0][0] is False

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    def test_read_radiation_retry_success(self, mock_modbus_tcp_client):
        """Test that read operation succeeds after retry."""

        # Setup mock

        mock_client_instance = MagicMock()

        mock_client_instance.connect.return_value = True

        # Mock read response - fail first time, succeed second time

        mock_response = MagicMock()

        mock_response.registers = [10000]

        mock_client_instance.read_input_registers.side_effect = [Exception("Timeout"), mock_response]

        mock_modbus_tcp_client.return_value = mock_client_instance

        # Create ModbusClient with retry configuration

        from modbuspython.config.config_manager import ConfigurationManager

        config = ConfigurationManager()

        config._config = {"modbus": {"retry_attempts": 3, "retry_backoff": 0.1, "timeout": 5.0}}  # Short delay for testing

        client = ModbusClient(ip="192.168.1.100", port=502, config_manager=config)

        client.connect()

        # Connect to signal

        radiation_spy = QSignalSpy(client.irradiance_updated)

        # Read radiation

        client.read_irradiance()

        # Verify read was attempted twice

        assert mock_client_instance.read_input_registers.call_count == 2

        # Verify signal was emitted with correct value

        assert len(radiation_spy) == 1

        assert radiation_spy[0][0] == pytest.approx(100.0)  # 10000 / 100

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    def test_write_setpoints_retry_success(self, mock_modbus_tcp_client):
        """Test that write operation succeeds after retry."""

        # Setup mock

        mock_client_instance = MagicMock()

        mock_client_instance.connect.return_value = True

        # Mock write response - fail first time, succeed second time

        mock_success_response = MagicMock()

        mock_success_response.isError.return_value = False

        mock_client_instance.write_register.side_effect = [
            Exception("Timeout"),  # First attempt fails
            Exception("Timeout"),  # First attempt fails (second register)
            mock_success_response,  # Second attempt succeeds
            mock_success_response,  # Second attempt succeeds (second register)
        ]

        mock_modbus_tcp_client.return_value = mock_client_instance

        # Create ModbusClient with retry configuration

        from modbuspython.config.config_manager import ConfigurationManager

        config = ConfigurationManager()

        config._config = {"modbus": {"retry_attempts": 3, "retry_backoff": 0.1, "timeout": 5.0}}  # Short delay for testing

        client = ModbusClient(ip="192.168.1.100", port=502, config_manager=config)

        client.connect()

        # Write setpoints

        client.write_setpoints(90, 45)

        # Verify write was attempted (2 registers * 2 attempts = 4 calls)

        assert mock_client_instance.write_register.call_count == 4

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    def test_retry_uses_config_values(self, mock_modbus_tcp_client):
        """Test that retry logic uses configuration values."""

        # Setup mock to always fail

        mock_client_instance = MagicMock()

        mock_client_instance.connect.return_value = False

        mock_modbus_tcp_client.return_value = mock_client_instance

        # Create ModbusClient with custom retry configuration

        from modbuspython.config.config_manager import ConfigurationManager

        config = ConfigurationManager()

        config._config = {
            "modbus": {
                "retry_attempts": 5,
                "retry_backoff": 0.05,
                "timeout": 5.0,
            }  # Custom value  # Short delay for testing
        }

        client = ModbusClient(ip="192.168.1.100", port=502, config_manager=config)

        # Verify retry strategy was initialized with config values

        assert client.retry_strategy.max_attempts == 5

        assert client.retry_strategy.initial_delay == 0.05

        # Attempt connection

        client.connect()

        # Verify connection was attempted 5 times (custom max_attempts)

        assert mock_client_instance.connect.call_count == 5
