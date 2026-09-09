"""Unit tests for AngleStateManager.

Tests cover:
- Singleton pattern enforcement
- Angle setting with validation
- Angle getting
- Mode setting and getting
- Signal emissions
- Validation error handling
- Signal blocking
- State debugging

Requirements validated: 1.2, 1.3, 7.1, 7.6
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtCore import QObject

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modbuspython.backend.angle_state_manager import AngleStateManager


class TestAngleStateManager:
    """Unit tests for AngleStateManager class."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton instance before each test."""
        AngleStateManager._instance = None
        yield
        AngleStateManager._instance = None

    @pytest.fixture
    def manager(self):
        """Create a fresh AngleStateManager instance for testing."""
        return AngleStateManager()

    # Test: Singleton pattern
    def test_singleton_pattern(self):
        """Test that AngleStateManager follows singleton pattern."""
        manager1 = AngleStateManager()
        manager2 = AngleStateManager()

        assert manager1 is manager2

        # Setting value in one should affect the other
        manager1._rot = 100.0
        assert manager2._rot == 100.0

    # Test: Initial state
    def test_initial_state(self, manager):
        """Test that manager initializes with correct default values."""
        assert manager._rot == 0.0
        assert manager._ele == 0.0
        assert manager._mode == "manual"
        assert manager._block_signal is False
        assert manager._last_source is None

    # Test: Set valid angles
    def test_set_valid_angles(self, manager):
        """Test setting valid rotation and elevation angles."""
        success, error = manager.set_angles(180.0, 45.0, source="test")

        assert success is True
        assert error is None
        assert manager._rot == 180.0
        assert manager._ele == 45.0
        assert manager._last_source == "test"

    # Test: Set angles at boundaries
    def test_set_angles_at_boundaries(self, manager):
        """Test setting angles at exact boundary values."""
        # Rotation boundaries
        success, error = manager.set_angles(0.0, 45.0)
        assert success is True
        assert manager._rot == 0.0

        success, error = manager.set_angles(360.0, 45.0)
        assert success is True
        assert manager._rot == 360.0

        # Elevation boundaries
        success, error = manager.set_angles(180.0, 0.0)
        assert success is True
        assert manager._ele == 0.0

        success, error = manager.set_angles(180.0, 145.0)
        assert success is True
        assert manager._ele == 145.0

    # Test: Set invalid rotation angle
    def test_set_invalid_rotation_angle(self, manager):
        """Test that invalid rotation angles are rejected."""
        # Too high
        success, error = manager.set_angles(400.0, 45.0)
        assert success is False
        assert error is not None
        assert "rotation" in error.lower()
        assert manager._rot == 0.0  # Should not change

        # Too low
        success, error = manager.set_angles(-10.0, 45.0)
        assert success is False
        assert error is not None
        assert "rotation" in error.lower()
        assert manager._rot == 0.0  # Should not change

    # Test: Set invalid elevation angle
    def test_set_invalid_elevation_angle(self, manager):
        """Test that invalid elevation angles are rejected."""
        # Too high
        success, error = manager.set_angles(180.0, 200.0)
        assert success is False
        assert error is not None
        assert "elevation" in error.lower()
        assert manager._ele == 0.0  # Should not change

        # Too low
        success, error = manager.set_angles(180.0, -5.0)
        assert success is False
        assert error is not None
        assert "elevation" in error.lower()
        assert manager._ele == 0.0  # Should not change

    # Test: Set non-numeric angles
    def test_set_non_numeric_angles(self, manager):
        """Test that non-numeric angle values are rejected."""
        success, error = manager.set_angles("180", 45.0)
        assert success is False
        assert error is not None

        success, error = manager.set_angles(180.0, "45")
        assert success is False
        assert error is not None

        success, error = manager.set_angles(None, 45.0)
        assert success is False
        assert error is not None

    # Test: Get angles
    def test_get_angles(self, manager):
        """Test getting current angle values."""
        manager._rot = 270.0
        manager._ele = 90.0

        rot, ele = manager.get_angles()
        assert rot == 270.0
        assert ele == 90.0

    # Test: Set mode
    def test_set_mode(self, manager):
        """Test setting operation mode."""
        assert manager._mode == "manual"

        manager.set_mode("auto", source="test")
        assert manager._mode == "auto"

        manager.set_mode("manual", source="test")
        assert manager._mode == "manual"

    # Test: Get mode
    def test_get_mode(self, manager):
        """Test getting current operation mode."""
        assert manager.get_mode() == "manual"

        manager._mode = "auto"
        assert manager.get_mode() == "auto"

    # Test: Signal emission on angle change
    def test_angles_changed_signal_emission(self, manager):
        """Test that angles_changed signal is emitted when angles change."""
        signal_spy = Mock()
        manager.angles_changed.connect(signal_spy)

        manager.set_angles(90.0, 30.0, source="test")

        # Signal should be emitted once
        signal_spy.assert_called_once()
        args = signal_spy.call_args[0]
        assert args[0] == 90.0  # rotation
        assert args[1] == 30.0  # elevation
        assert args[2] == "test"  # source

    # Test: Signal not emitted when angles don't change
    def test_angles_changed_signal_not_emitted_when_same(self, manager):
        """Test that signal is not emitted when angles don't actually change."""
        manager._rot = 100.0
        manager._ele = 50.0

        signal_spy = Mock()
        manager.angles_changed.connect(signal_spy)

        # Set to same values
        manager.set_angles(100.0, 50.0, source="test")

        # Signal should not be emitted
        signal_spy.assert_not_called()

    # Test: Signal emission on mode change
    def test_mode_changed_signal_emission(self, manager):
        """Test that mode_changed signal is emitted when mode changes."""
        signal_spy = Mock()
        manager.mode_changed.connect(signal_spy)

        manager.set_mode("auto", source="test")

        # Signal should be emitted once
        signal_spy.assert_called_once()
        args = signal_spy.call_args[0]
        assert args[0] == "auto"  # mode
        assert args[1] == "test"  # source

    # Test: Signal not emitted when mode doesn't change
    def test_mode_changed_signal_not_emitted_when_same(self, manager):
        """Test that signal is not emitted when mode doesn't actually change."""
        manager._mode = "auto"

        signal_spy = Mock()
        manager.mode_changed.connect(signal_spy)

        # Set to same mode
        manager.set_mode("auto", source="test")

        # Signal should not be emitted
        signal_spy.assert_not_called()

    # Test: Validation error signal emission
    def test_validation_error_signal_emission(self, manager):
        """Test that validation_error signal is emitted on validation failure."""
        signal_spy = Mock()
        manager.validation_error.connect(signal_spy)

        # Try to set invalid angle
        manager.set_angles(400.0, 45.0)

        # Validation error signal should be emitted
        signal_spy.assert_called_once()
        error_message = signal_spy.call_args[0][0]
        assert "rotation" in error_message.lower()

    # Test: Block signals
    def test_block_signals(self, manager):
        """Test that signal blocking prevents angle updates."""
        manager.block_signals(True)

        success, error = manager.set_angles(180.0, 45.0)

        # Should return success but not update angles
        assert success is True
        assert error is None
        assert manager._rot == 0.0  # Should not change
        assert manager._ele == 0.0  # Should not change

    # Test: Unblock signals
    def test_unblock_signals(self, manager):
        """Test that unblocking signals allows angle updates."""
        manager.block_signals(True)
        manager.set_angles(180.0, 45.0)
        assert manager._rot == 0.0  # Blocked

        manager.block_signals(False)
        manager.set_angles(270.0, 90.0)
        assert manager._rot == 270.0  # Not blocked
        assert manager._ele == 90.0

    # Test: Get last source
    def test_get_last_source(self, manager):
        """Test getting the source of the last angle change."""
        assert manager.get_last_source() is None

        manager.set_angles(180.0, 45.0, source="ui")
        assert manager.get_last_source() == "ui"

        manager.set_angles(270.0, 90.0, source="modbus")
        assert manager.get_last_source() == "modbus"

    # Test: Debug state
    def test_debug_state(self, manager):
        """Test debug_state method returns complete state information."""
        manager._rot = 180.0
        manager._ele = 45.0
        manager._mode = "auto"
        manager._block_signal = True
        manager._last_source = "test"

        state = manager.debug_state()

        assert state["rot"] == 180.0
        assert state["ele"] == 45.0
        assert state["mode"] == "auto"
        assert state["block_signal"] is True
        assert state["last_source"] == "test"

    # Test: Multiple angle updates
    def test_multiple_angle_updates(self, manager):
        """Test multiple sequential angle updates."""
        signal_spy = Mock()
        manager.angles_changed.connect(signal_spy)

        manager.set_angles(90.0, 30.0, source="test1")
        manager.set_angles(180.0, 60.0, source="test2")
        manager.set_angles(270.0, 90.0, source="test3")

        # Signal should be emitted three times
        assert signal_spy.call_count == 3

        # Final state should be last values
        assert manager._rot == 270.0
        assert manager._ele == 90.0
        assert manager._last_source == "test3"

    # Test: Angle validation with ValidationService
    def test_angle_validation_uses_validation_service(self, manager):
        """Test that angle validation uses ValidationService."""
        # The manager should have a ValidationService instance
        assert manager._validation_service is not None

        # Test that validation is actually performed
        success, error = manager.set_angles(400.0, 45.0)
        assert success is False
        assert error is not None

        success, error = manager.set_angles(180.0, 200.0)
        assert success is False
        assert error is not None

    # Test: Source parameter is optional
    def test_source_parameter_optional(self, manager):
        """Test that source parameter is optional in set_angles and set_mode."""
        # Should work without source
        success, error = manager.set_angles(180.0, 45.0)
        assert success is True

        manager.set_mode("auto")
        assert manager._mode == "auto"

    # Test: Angle change detection
    def test_angle_change_detection(self, manager):
        """Test that angle changes are correctly detected."""
        signal_spy = Mock()
        manager.angles_changed.connect(signal_spy)

        # Set initial angles
        manager.set_angles(100.0, 50.0)
        assert signal_spy.call_count == 1

        # Change only rotation
        manager.set_angles(200.0, 50.0)
        assert signal_spy.call_count == 2

        # Change only elevation
        manager.set_angles(200.0, 75.0)
        assert signal_spy.call_count == 3

        # No change
        manager.set_angles(200.0, 75.0)
        assert signal_spy.call_count == 3  # Should not increment

    # Test: Validation error doesn't change state
    def test_validation_error_preserves_state(self, manager):
        """Test that validation errors don't change the manager's state."""
        # Set valid initial state
        manager.set_angles(180.0, 45.0, source="initial")

        initial_rot = manager._rot
        initial_ele = manager._ele
        initial_source = manager._last_source

        # Try to set invalid angles
        success, error = manager.set_angles(400.0, 200.0, source="invalid")

        # State should be unchanged
        assert success is False
        assert manager._rot == initial_rot
        assert manager._ele == initial_ele
        assert manager._last_source == initial_source

    # Test: QObject inheritance
    def test_qobject_inheritance(self, manager):
        """Test that AngleStateManager properly inherits from QObject."""
        assert isinstance(manager, QObject)

        # Should have signal attributes
        assert hasattr(manager, "angles_changed")
        assert hasattr(manager, "mode_changed")
        assert hasattr(manager, "validation_error")

    # Test: Constant values
    def test_constant_values(self):
        """Test that class constants are correctly defined."""
        assert AngleStateManager.ROT_MIN == 0
        assert AngleStateManager.ROT_MAX == 360
        assert AngleStateManager.ELE_MIN == 0
        assert AngleStateManager.ELE_MAX == 145

    # Test: Partial validation failure (rotation valid, elevation invalid)
    def test_partial_validation_failure_rotation_valid(self, manager):
        """Test that if rotation is valid but elevation is invalid, both are rejected."""
        success, error = manager.set_angles(180.0, 200.0)

        assert success is False
        assert error is not None
        assert "elevation" in error.lower()

        # Neither angle should be updated
        assert manager._rot == 0.0
        assert manager._ele == 0.0

    # Test: Partial validation failure (rotation invalid, elevation valid)
    def test_partial_validation_failure_elevation_valid(self, manager):
        """Test that if elevation is valid but rotation is invalid, both are rejected."""
        success, error = manager.set_angles(400.0, 45.0)

        assert success is False
        assert error is not None
        assert "rotation" in error.lower()

        # Neither angle should be updated
        assert manager._rot == 0.0
        assert manager._ele == 0.0

    # Test: Float precision
    def test_float_precision(self, manager):
        """Test that float values are handled with proper precision."""
        success, error = manager.set_angles(180.123456, 45.654321)

        assert success is True
        assert manager._rot == 180.123456
        assert manager._ele == 45.654321

    # Test: Integer angles
    def test_integer_angles(self, manager):
        """Test that integer angle values are accepted."""
        success, error = manager.set_angles(180, 45)

        assert success is True
        assert manager._rot == 180
        assert manager._ele == 45

    # Test: Mode values
    def test_mode_values(self, manager):
        """Test that different mode values are accepted."""
        manager.set_mode("manual")
        assert manager._mode == "manual"

        manager.set_mode("auto")
        assert manager._mode == "auto"

        # Should accept any string value (no validation on mode)
        manager.set_mode("custom_mode")
        assert manager._mode == "custom_mode"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
