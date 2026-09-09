"""PyJS Bridge for communication between Python and JavaScript in the 3D viewer."""

from PyQt6.QtCore import QObject, pyqtSlot

from ..data_access.logging_service import LoggingService


class PyJsBridge(QObject):
    """Bridge between Python and JavaScript for the 3D solar tracker viewer.

    Exposes methods that JavaScript can call via QWebChannel.
    """

    def __init__(self):
        super().__init__()
        self.logger = LoggingService()

    @pyqtSlot(float, float)
    def onAnglesChanged(self, rot: float, ele: float) -> None:
        """Called from JS when angles change in the 3D viewer."""
        self.logger.debug(f"Angles received from 3D viewer: Rotation={rot}, Elevation={ele}")

    @pyqtSlot(float, float, float, float, float, float)
    def onCameraChanged(self, x: float, y: float, z: float, tx: float, ty: float, tz: float) -> None:
        """Called from JS when camera position changes in the 3D viewer."""
        self.logger.debug(f"Camera: Pos=({x:.2f},{y:.2f},{z:.2f}) Target=({tx:.2f},{ty:.2f},{tz:.2f})")
