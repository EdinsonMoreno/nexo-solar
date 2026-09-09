"""Centralized angle state management for SolarSense SCADA.

This module provides a singleton manager for tracking and propagating angle
and operation mode state changes throughout the application. It ensures
consistent state management and reactive UI updates via Qt signals.

Requirements validated: 1.3, 1.6, 7.1
"""

from PyQt6.QtCore import QObject, pyqtSignal
from typing import Tuple, Optional, Dict, Any
from ..data_access.logging_service import LoggingService
from .validation_service import ValidationService


class AngleStateManager(QObject):
    """Singleton manager for centralizing and propagating angle and mode state.

    This class provides a single source of truth for rotation/elevation angles
    and operation mode (manual/auto) across the entire application. It validates
    all angle changes and emits signals to synchronize UI and backend components.

    Always use AngleStateManager to read/write angles and mode from any part of
    the application. The angles_changed and mode_changed signals enable reactive
    synchronization between UI and backend.

    Signals:
        angles_changed (float, float, object): Emitted when angles change (rot, ele, source)
        mode_changed (str, object): Emitted when mode changes ('manual' or 'auto', source)
        validation_error (str): Emitted when angle validation fails (error message)

    Attributes:
        ROT_MIN (int): Minimum rotation angle (0)
        ROT_MAX (int): Maximum rotation angle (360)
        ELE_MIN (int): Minimum elevation angle (0)
        ELE_MAX (int): Maximum elevation angle (145)

    Requirements validated: 1.3, 1.6, 7.1
    """

    # Señales para notificar cambios
    angles_changed = pyqtSignal(float, float, object)  # rot, ele, source
    mode_changed = pyqtSignal(str, object)  # 'manual' o 'auto', source
    validation_error = pyqtSignal(str)  # error message

    _instance: Optional["AngleStateManager"] = None

    # Rango permitido para los ángulos
    ROT_MIN: int = 0
    ROT_MAX: int = 360
    ELE_MIN: int = 0
    ELE_MAX: int = 145

    # Anotaciones de tipo para atributos de instancia inicializados en __new__
    _rot: float
    _ele: float
    _mode: str
    _block_signal: bool
    _last_source: Optional[Any]
    _validation_service: ValidationService

    def __new__(cls) -> "AngleStateManager":
        """Create or return the singleton instance.

        Ensures only one instance of AngleStateManager exists. Initializes
        QObject and all attributes only once.

        Returns:
            AngleStateManager: The singleton instance
        """
        if cls._instance is None:
            logger = LoggingService()
            logger.debug("Creating AngleStateManager singleton instance")
            obj = super().__new__(cls)
            super(cls, obj).__init__()  # Inicializa QObject solo una vez
            obj._rot = 0.0
            obj._ele = 0.0
            obj._mode = "manual"
            obj._block_signal = False
            obj._last_source = None
            obj._validation_service = ValidationService()
            cls._instance = obj
            logger.debug("AngleStateManager singleton instance created successfully")
        return cls._instance

    def __init__(self) -> None:
        """Initialize the angle state manager.

        Note: Actual initialization happens in __new__ to ensure singleton pattern.
        This method is kept empty to prevent re-initialization.
        """

    def set_angles(self, rot: float, ele: float, source: Optional[Any] = None) -> Tuple[bool, Optional[str]]:
        """Update global rotation and elevation angles.

        Validates and normalizes the values before updating state. Propagates
        changes throughout the application via the angles_changed signal.
        The 'source' parameter helps prevent feedback loops and identify the
        origin of changes.

        Args:
            rot: Rotation angle (0-360)
            ele: Elevation angle (0-145)
            source: Source of the change (optional, for tracking)

        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
                - success: True if angles were valid and updated, False otherwise
                - error_message: None if successful, error description if validation failed

        Requirements validated: 7.1
        """
        logger = LoggingService()
        logger.debug(f"set_angles called: rot={rot}, ele={ele}, source={source}")

        if self._block_signal:
            logger.debug("set_angles blocked by _block_signal flag")
            return True, None

        # Validate rotation angle
        is_valid_rot, error_rot = self._validation_service.validate_rotation(rot)
        if not is_valid_rot:
            logger.warning(f"Rotation angle validation failed: {error_rot}")
            self.validation_error.emit(error_rot)
            return False, error_rot

        # Validate elevation angle
        is_valid_ele, error_ele = self._validation_service.validate_elevation(ele)
        if not is_valid_ele:
            logger.warning(f"Elevation angle validation failed: {error_ele}")
            self.validation_error.emit(error_ele)
            return False, error_ele

        # Both angles are valid, update state
        changed = (self._rot != rot) or (self._ele != ele)
        self._rot = rot
        self._ele = ele

        if changed:
            self._last_source = source
            logger.debug(f"Emitting angles_changed signal: rot={rot}, ele={ele}, source={source}")
            self.angles_changed.emit(rot, ele, source)

        return True, None

    def get_angles(self) -> Tuple[float, float]:
        """Get current angles.

        Returns:
            Tuple[float, float]: Current (rotation, elevation) angles
        """
        logger = LoggingService()
        logger.debug(f"get_angles: rot={self._rot}, ele={self._ele}")
        return self._rot, self._ele

    def set_mode(self, mode: str, source: Optional[Any] = None) -> None:
        """Change global operation mode ('manual' or 'auto').

        Propagates the change via the mode_changed signal. The 'source' parameter
        helps identify the origin of the change.

        Args:
            mode: Operation mode ('manual' or 'auto')
            source: Source of the change (optional, for tracking)
        """
        logger = LoggingService()
        if self._mode != mode:
            self._mode = mode
            logger.info(f"Operation mode changed to '{mode}' (source: {source})")
            self.mode_changed.emit(mode, source)

    def get_mode(self) -> str:
        """Get current operation mode.

        Returns:
            str: Current mode ('manual' or 'auto')
        """
        return self._mode

    def block_signals(self, block: bool = True) -> None:
        """Block or unblock signal emission.

        Useful for preventing signal emission during batch updates or
        programmatic changes that shouldn't trigger reactions.

        Args:
            block: True to block signals, False to unblock
        """
        self._block_signal = block

    def _normalize(self, value: float, minv: float, maxv: float) -> float:
        """Normalize a value within a range.

        Converts value to float and clamps it between min and max values.

        Args:
            value: Value to normalize
            minv: Minimum allowed value
            maxv: Maximum allowed value

        Returns:
            float: Normalized value clamped to [minv, maxv]
        """
        try:
            value = float(value)
        except Exception:
            value = minv
        return max(minv, min(maxv, value))

    def get_last_source(self) -> Optional[Any]:
        """Get the last source of angle change.

        Returns:
            Optional[Any]: Last source object or None
        """
        return self._last_source

    def debug_state(self) -> Dict[str, Any]:
        """Get current state for debugging purposes.

        Returns:
            Dict[str, Any]: Dictionary containing current state:
                - rot: Current rotation angle
                - ele: Current elevation angle
                - mode: Current operation mode
                - block_signal: Whether signals are blocked
                - last_source: Last source of change
        """
        return {
            "rot": self._rot,
            "ele": self._ele,
            "mode": self._mode,
            "block_signal": self._block_signal,
            "last_source": self._last_source,
        }
