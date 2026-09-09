"""Integration tests for UI → AngleStateManager → ModbusClient flow.



Tests the complete flow from UI input through angle state management


to Modbus communication, verifying that:


- UI changes propagate to AngleStateManager


- AngleStateManager validates and updates state


- ModbusClient receives and writes the correct values


- Signals are emitted correctly throughout the chain



These tests use mocks for pymodbus to avoid requiring actual hardware.
"""

import sys


import pytest


from pathlib import Path


from unittest.mock import Mock, patch, MagicMock


from PyQt6.QtCore import QTimer


from PyQt6.QtTest import QSignalSpy

# Add parent directory to path for imports


sys.path.insert(0, str(Path(__file__).parent.parent.parent))


from modbuspython.backend.angle_state_manager import AngleStateManager


from modbuspython.data_access.modbus_client import ModbusClient


from modbuspython.config.config_manager import ConfigurationManager


class TestUIToModbusFlow:
    """Test complete flow from UI input to Modbus write operation."""

    @pytest.fixture
    def angle_manager(self):
        """Create a fresh AngleStateManager instance for each test."""

        # Reset singleton

        AngleStateManager._instance = None

        manager = AngleStateManager()

        yield manager

        # Cleanup

        AngleStateManager._instance = None

    @pytest.fixture
    def config_manager(self):
        """Create a ConfigurationManager with test configuration."""

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
            "angles": {"rotation_min": 0, "rotation_max": 360, "elevation_min": 0, "elevation_max": 145},
        }

        return config

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    def test_valid_angle_update_flow(self, mock_modbus_tcp_client, angle_manager, config_manager):
        """Test that valid angle updates flow correctly from UI to Modbus."""

        # Setup mock Modbus client

        mock_client_instance = MagicMock()

        mock_client_instance.connect.return_value = True

        mock_success_response = MagicMock()

        mock_success_response.isError.return_value = False

        mock_client_instance.write_register.return_value = mock_success_response

        mock_modbus_tcp_client.return_value = mock_client_instance

        # Create and connect ModbusClient

        modbus_client = ModbusClient(
            ip=config_manager.get("modbus.host"), port=config_manager.get("modbus.port"), config_manager=config_manager
        )

        modbus_client.connect()

        # Connect signals

        angle_spy = QSignalSpy(angle_manager.angles_changed)

        # Simulate UI input: user sets angles to 90° rotation, 45° elevation

        success, error = angle_manager.set_angles(90.0, 45.0, source="UI")

        # Verify angle manager accepted the values

        assert success is True

        assert error is None

        assert len(angle_spy) == 1

        assert angle_spy[0][0] == 90.0

        assert angle_spy[0][1] == 45.0

        assert angle_spy[0][2] == "UI"

        # Verify angle manager state updated

        rot, ele = angle_manager.get_angles()

        assert rot == 90.0

        assert ele == 45.0

        # Simulate ModbusClient responding to angle change

        modbus_client.write_setpoints(90.0, 45.0)

        # Verify Modbus write was called with correct values

        # Note: ModbusClient uses retry logic, so there may be multiple attempts

        # We just verify that the correct registers were written with correct values

        calls = mock_client_instance.write_register.call_args_list

        assert len(calls) >= 2  # At least 2 writes (rotation + elevation)

        # Check that rotation register was written with value 90

        rotation_writes = [c for c in calls if c[1]["address"] == 1]  # reg_motor1

        assert len(rotation_writes) > 0

        assert rotation_writes[0][1]["value"] == 90

        # Check that elevation register was written with value 45

        elevation_writes = [c for c in calls if c[1]["address"] == 2]  # reg_motor2

        assert len(elevation_writes) > 0

        assert elevation_writes[0][1]["value"] == 45

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    def test_invalid_angle_rejected_by_manager(self, mock_modbus_tcp_client, angle_manager, config_manager):
        """Test that invalid angles are rejected by AngleStateManager and don't reach Modbus."""

        # Setup mock Modbus client

        mock_client_instance = MagicMock()

        mock_client_instance.connect.return_value = True

        mock_modbus_tcp_client.return_value = mock_client_instance

        # Create and connect ModbusClient

        modbus_client = ModbusClient(
            ip=config_manager.get("modbus.host"), port=config_manager.get("modbus.port"), config_manager=config_manager
        )

        modbus_client.connect()

        # Connect signals

        angle_spy = QSignalSpy(angle_manager.angles_changed)

        error_spy = QSignalSpy(angle_manager.validation_error)

        # Simulate UI input: user tries to set invalid rotation angle (400°)

        success, error = angle_manager.set_angles(400.0, 45.0, source="UI")

        # Verify angle manager rejected the values

        assert success is False

        assert error is not None

        assert "rotation" in error.lower()

        # Verify angles_changed signal was NOT emitted

        assert len(angle_spy) == 0

        # Verify validation_error signal WAS emitted

        assert len(error_spy) == 1

        # Verify angle manager state did NOT change

        rot, ele = angle_manager.get_angles()

        assert rot == 0.0  # Default value

        assert ele == 0.0  # Default value

        # Verify Modbus write was NOT called

        mock_client_instance.write_register.assert_not_called()

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    def test_multiple_angle_updates_in_sequence(self, mock_modbus_tcp_client, angle_manager, config_manager):
        """Test that multiple angle updates are handled correctly in sequence."""

        # Setup mock Modbus client

        mock_client_instance = MagicMock()

        mock_client_instance.connect.return_value = True

        mock_success_response = MagicMock()

        mock_success_response.isError.return_value = False

        mock_client_instance.write_register.return_value = mock_success_response

        mock_modbus_tcp_client.return_value = mock_client_instance

        # Create and connect ModbusClient

        modbus_client = ModbusClient(
            ip=config_manager.get("modbus.host"), port=config_manager.get("modbus.port"), config_manager=config_manager
        )

        modbus_client.connect()

        # Connect signals

        angle_spy = QSignalSpy(angle_manager.angles_changed)

        # Simulate sequence of UI inputs

        test_angles = [(45.0, 30.0), (90.0, 60.0), (180.0, 90.0), (270.0, 120.0)]

        for rot, ele in test_angles:

            # Update angles

            success, error = angle_manager.set_angles(rot, ele, source="UI")

            assert success is True

            # Write to Modbus

            modbus_client.write_setpoints(rot, ele)

        # Verify all angle changes were emitted

        assert len(angle_spy) == len(test_angles)

        # Verify final state

        final_rot, final_ele = angle_manager.get_angles()

        assert final_rot == test_angles[-1][0]

        assert final_ele == test_angles[-1][1]

        # Verify Modbus writes were called

        # Each angle update writes 2 registers (rotation + elevation)

        # With retry logic, there may be multiple attempts per register

        assert mock_client_instance.write_register.call_count >= len(test_angles) * 2

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    def test_mode_change_propagation(self, mock_modbus_tcp_client, angle_manager, config_manager):
        """Test that mode changes propagate correctly through the system."""

        # Setup mock Modbus client

        mock_client_instance = MagicMock()

        mock_client_instance.connect.return_value = True

        mock_modbus_tcp_client.return_value = mock_client_instance

        # Create ModbusClient

        modbus_client = ModbusClient(
            ip=config_manager.get("modbus.host"), port=config_manager.get("modbus.port"), config_manager=config_manager
        )

        modbus_client.connect()

        # Connect signals

        mode_spy = QSignalSpy(angle_manager.mode_changed)

        # Verify initial mode

        assert angle_manager.get_mode() == "manual"

        # Simulate UI changing mode to auto

        angle_manager.set_mode("auto", source="UI")

        # Verify mode changed

        assert angle_manager.get_mode() == "auto"

        # Verify signal was emitted

        assert len(mode_spy) == 1

        assert mode_spy[0][0] == "auto"

        assert mode_spy[0][1] == "UI"

        # Change back to manual

        angle_manager.set_mode("manual", source="UI")

        # Verify mode changed again

        assert angle_manager.get_mode() == "manual"

        assert len(mode_spy) == 2

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    def test_modbus_connection_failure_handling(self, mock_modbus_tcp_client, angle_manager, config_manager):
        """Test that Modbus connection failures are handled gracefully."""

        # Setup mock Modbus client to fail connection

        mock_client_instance = MagicMock()

        mock_client_instance.connect.return_value = False

        mock_modbus_tcp_client.return_value = mock_client_instance

        # Create ModbusClient

        modbus_client = ModbusClient(
            ip=config_manager.get("modbus.host"), port=config_manager.get("modbus.port"), config_manager=config_manager
        )

        # Connect signals

        connection_spy = QSignalSpy(modbus_client.conexion_cambiada)

        # Attempt connection

        modbus_client.connect()

        # Verify connection failed

        assert modbus_client.is_connected is False

        assert len(connection_spy) == 1

        assert connection_spy[0][0] is False

        # Angle manager should still work

        success, error = angle_manager.set_angles(90.0, 45.0, source="UI")

        assert success is True

        # But Modbus writes should not be attempted when not connected

        # (ModbusClient checks connection before writing)

        modbus_client.write_setpoints(90.0, 45.0)

        mock_client_instance.write_register.assert_not_called()

    @patch("modbuspython.data_access.modbus_client.ModbusTcpClient")
    def test_boundary_angle_values(self, mock_modbus_tcp_client, angle_manager, config_manager):
        """Test that boundary angle values are handled correctly."""

        # Setup mock Modbus client

        mock_client_instance = MagicMock()

        mock_client_instance.connect.return_value = True

        mock_success_response = MagicMock()

        mock_success_response.isError.return_value = False

        mock_client_instance.write_register.return_value = mock_success_response

        mock_modbus_tcp_client.return_value = mock_client_instance

        # Create and connect ModbusClient

        modbus_client = ModbusClient(
            ip=config_manager.get("modbus.host"), port=config_manager.get("modbus.port"), config_manager=config_manager
        )

        modbus_client.connect()

        # Test minimum values

        success, error = angle_manager.set_angles(0.0, 0.0, source="UI")

        assert success is True

        modbus_client.write_setpoints(0.0, 0.0)

        # Test maximum values

        success, error = angle_manager.set_angles(360.0, 145.0, source="UI")

        assert success is True

        modbus_client.write_setpoints(360.0, 145.0)

        # Test just below minimum (should fail)

        success, error = angle_manager.set_angles(-0.1, 0.0, source="UI")

        assert success is False

        # Test just above maximum (should fail)

        success, error = angle_manager.set_angles(360.1, 145.0, source="UI")

        assert success is False

        success, error = angle_manager.set_angles(180.0, 145.1, source="UI")

        assert success is False


if __name__ == "__main__":

    pytest.main([__file__, "-v"])
