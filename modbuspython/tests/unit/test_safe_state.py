"""
Unit tests for safe state behavior in ModbusClient.

Tests verify that:
1. Write operations are blocked in safe state
2. Read operations continue in safe state
3. Safe state can be exited manually
4. Safe state is entered on critical errors

Requirements: 4.10
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from modbuspython.data_access.modbus_client import ModbusClient
from modbuspython.exceptions import ModbusConnectionError, ModbusOperationError


class TestSafeStateBehavior:
    """Test suite for safe state behavior."""

    @pytest.fixture
    def modbus_client(self):
        """Create a ModbusClient instance for testing."""
        with patch("modbuspython.data_access.modbus_client.ModbusTcpClient"):
            client = ModbusClient(ip="192.168.1.100", port=502)
            client.is_connected = True
            client.client = Mock()
            yield client

    def test_write_blocked_in_safe_state(self, modbus_client):
        """Test that write operations are blocked when in safe state."""
        # Enter safe state
        modbus_client.safe_state = True

        # Attempt to write setpoints
        modbus_client.escribir_consignas(90, 45)

        # Verify that write_register was NOT called
        modbus_client.client.write_register.assert_not_called()

    def test_read_continues_in_safe_state(self, modbus_client):
        """Test that read operations continue even in safe state."""
        # Enter safe state
        modbus_client.safe_state = True

        # Mock successful read response
        mock_response = Mock()
        mock_response.isError.return_value = False
        mock_response.registers = [1234]
        modbus_client.client.read_input_registers.return_value = mock_response

        # Attempt to read radiation
        modbus_client.leer_radiacion()

        # Verify that read_input_registers WAS called (reads continue in safe state)
        modbus_client.client.read_input_registers.assert_called_once()

    def test_safe_state_entered_on_write_failure(self, modbus_client):
        """Test that safe state is entered when write operation fails after retries."""
        # Mock write failure
        modbus_client.client.write_register.side_effect = ModbusOperationError("Write failed")

        # Configure retry strategy to fail quickly
        modbus_client.retry_strategy.max_attempts = 1

        # Attempt to write setpoints
        modbus_client.escribir_consignas(90, 45)

        # Verify system entered safe state
        assert modbus_client.is_in_safe_state() is True

    def test_safe_state_entered_on_connection_failure(self, modbus_client):
        """Test that safe state is entered when connection fails after retries."""
        # Mock connection failure - need to mock the ModbusTcpClient constructor
        with patch("modbuspython.data_access.modbus_client.ModbusTcpClient") as mock_tcp_client:
            mock_instance = Mock()
            mock_instance.connect.return_value = False
            mock_tcp_client.return_value = mock_instance

            # Configure retry strategy to fail quickly
            modbus_client.retry_strategy.max_attempts = 1

            # Attempt to connect
            modbus_client.conectar()

            # Verify system entered safe state
            assert modbus_client.is_in_safe_state() is True

    def test_exit_safe_state_manually(self, modbus_client):
        """Test that safe state can be exited manually."""
        # Enter safe state
        modbus_client.safe_state = True
        assert modbus_client.is_in_safe_state() is True

        # Exit safe state manually
        modbus_client.exit_safe_state()

        # Verify system exited safe state
        assert modbus_client.is_in_safe_state() is False

    def test_safe_state_cleared_on_successful_connection(self, modbus_client):
        """Test that safe state is cleared when connection succeeds."""
        # Enter safe state
        modbus_client.safe_state = True

        # Mock successful connection
        with patch.object(modbus_client, "client") as mock_client:
            mock_client.connect.return_value = True

            # Attempt to connect
            modbus_client.conectar()

            # Verify system exited safe state
            assert modbus_client.is_in_safe_state() is False

    def test_retry_exhausted_signal_emitted(self, modbus_client):
        """Test that retry_exhausted signal is emitted when entering safe state."""
        # Create a mock signal handler
        signal_handler = Mock()
        modbus_client.retry_exhausted.connect(signal_handler)

        # Mock write failure
        modbus_client.client.write_register.side_effect = ModbusOperationError("Write failed")
        modbus_client.retry_strategy.max_attempts = 1

        # Attempt to write setpoints
        modbus_client.escribir_consignas(90, 45)

        # Verify signal was emitted
        signal_handler.assert_called_once()
        args = signal_handler.call_args[0]
        assert args[0] == "Write Setpoints"  # operation name
        # Error message contains details about the failure
        assert "192.168.1.100:502" in args[1] or "Write" in args[1]  # error message contains relevant info

    def test_write_succeeds_after_exiting_safe_state(self, modbus_client):
        """Test that write operations work after exiting safe state."""
        # Enter safe state
        modbus_client.safe_state = True

        # Exit safe state
        modbus_client.exit_safe_state()

        # Mock successful write
        mock_response = Mock()
        mock_response.isError.return_value = False
        modbus_client.client.write_register.return_value = mock_response

        # Attempt to write setpoints
        modbus_client.escribir_consignas(90, 45)

        # Verify that write_register WAS called
        assert modbus_client.client.write_register.call_count == 2  # Motor1 and Motor2

    def test_safe_state_persists_across_read_operations(self, modbus_client):
        """Test that safe state persists even when read operations succeed."""
        # Enter safe state
        modbus_client.safe_state = True

        # Mock successful read
        mock_response = Mock()
        mock_response.isError.return_value = False
        mock_response.registers = [1234]
        modbus_client.client.read_input_registers.return_value = mock_response

        # Perform read operation
        modbus_client.leer_radiacion()

        # Verify safe state persists
        assert modbus_client.is_in_safe_state() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
