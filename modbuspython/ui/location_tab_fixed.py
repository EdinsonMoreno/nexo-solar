"""Location Tab for Nexo Solar - Refactored.

Main container widget that composes:
- LocationSetupTab: Equipment location with map and search
- SolarTrackerTab: Automatic solar angle calculations
- ManualControlPanel: Manual angle controls with 3D viewer
"""

import datetime
import os

from PyQt6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QFrame,
)
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtCore import Qt, QTimer

from ..data_access.logging_service import LoggingService
from ..backend.validation_service import ValidationService
from .pyjs_bridge import PyJsBridge
from .location_setup_tab import LocationSetupTab
from .manual_control_panel import ManualControlPanel
from .solar_tracker_tab import SolarTrackerTab


class LocationTab(QWidget):
    """Main location tab containing sub-tabs for solar tracking, location setup, and manual control."""

    def __init__(self):
        super().__init__()
        self.logger = LoggingService()
        self.validation_service = ValidationService()
        self._build_ui()
        self._setup_connections()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 10, 20, 10)

        main_layout.addLayout(self._build_logo_row())
        main_layout.addSpacing(10)

        panel = self._build_main_panel()
        main_layout.addWidget(panel)

    def _build_logo_row(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        logo = QLabel()
        logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../assets/Logo.png"))

        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            if not pixmap.isNull():
                logo.setPixmap(
                    pixmap.scaled(220, 70, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                )
            else:
                self._set_logo_text(logo)
        else:
            self._set_logo_text(logo)

        logo.setStyleSheet("background: transparent;")
        layout.addWidget(logo)
        layout.addStretch()
        return layout

    @staticmethod
    def _set_logo_text(logo: QLabel) -> None:
        logo.setText("Nexo Solar")
        logo.setFont(QFont("Arial", 28, QFont.Weight.Bold))

    def _build_main_panel(self) -> QFrame:
        panel = QFrame()
        panel.setStyleSheet("QFrame { background: #c0c2c4; border: 2px solid #888; border-radius: 8px; }")
        panel_layout = QVBoxLayout(panel)

        tabs = QTabWidget()
        tabs.setTabPosition(QTabWidget.TabPosition.North)
        tabs.setStyleSheet(
            "QTabBar::tab { height: 28px; width: 150px; font: 12px Arial; background: #d3d3d3; "
            "border: 1px solid #888; border-bottom: none; } QTabBar::tab:selected { background: #e6e6e6; color: #005fa3; }"
        )

        # Create sub-tabs
        self.location_setup_tab = LocationSetupTab()
        tabs.addTab(self.location_setup_tab, "Ubicacion del Equipo")

        self.solar_tracker_tab = SolarTrackerTab()
        tabs.addTab(self.solar_tracker_tab, "Seguidor Solar Automatico")

        self.manual_control_panel = ManualControlPanel()
        tabs.addTab(self.manual_control_panel, "Control Manual")

        panel_layout.addWidget(tabs)
        return panel

    def _setup_connections(self) -> None:
        # Sync coordinates from location setup to solar tracker
        self.location_setup_tab.coordinates_applied.connect(self._apply_coordinates_to_tracker)

        # Auto-update hour
        self._auto_time_timer = QTimer(self)
        self._auto_time_timer.timeout.connect(self._update_hour_spin)
        self._auto_time_timer.start(1000)

        # 3D viewer web channel
        self.web_channel = self.manual_control_panel.setup_web_channel()
        self.pyjs = PyJsBridge()
        self.web_channel.registerObject("pyjs", self.pyjs)

    def _apply_coordinates_to_tracker(self, lat: float, lon: float) -> None:
        self.solar_tracker_tab.lat_spin.setValue(lat)
        self.solar_tracker_tab.lon_spin.setValue(lon)

    def _update_hour_spin(self) -> None:
        self.solar_tracker_tab.hora_spin.setValue(datetime.datetime.now().hour)

    def sync_location_from_tracker(self, lat: float, lon: float) -> None:
        self.location_setup_tab.sync_from_calculation(lat, lon)

    def cleanup(self) -> None:
        self.logger.debug("LocationTab cleanup: releasing resources")
        try:
            if hasattr(self, "_auto_time_timer"):
                self._auto_time_timer.stop()
                self._auto_time_timer.deleteLater()
        except Exception as e:
            self.logger.error(f"Error stopping timer: {e}")

        try:
            self.manual_control_panel.cleanup_3d_viewer()
        except Exception as e:
            self.logger.error(f"Error cleaning up 3D viewer: {e}")

        try:
            if hasattr(self, "web_channel") and hasattr(self, "pyjs"):
                try:
                    self.web_channel.deregisterObject(self.pyjs)
                except (RuntimeError, AttributeError):
                    pass
                self.web_channel.deleteLater()
                self.pyjs.deleteLater()
        except Exception as e:
            self.logger.error(f"Error cleaning up web channel: {e}")

        self.logger.info("LocationTab cleanup completed")

    def closeEvent(self, event) -> None:
        self.cleanup()
        event.accept()
