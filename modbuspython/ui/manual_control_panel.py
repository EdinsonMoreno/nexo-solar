"""Manual Control Panel widget with 3D viewer.

Provides sliders and spinboxes for manual angle control,
plus an integrated 3D solar tracker viewer via QWebEngineView.
"""

import os

from PyQt6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QPushButton,
    QSlider,
    QSpinBox,
    QMessageBox,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QUrl

from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel

from ..data_access.logging_service import LoggingService
from ..backend.validation_service import ValidationService


class ManualControlPanel(QWidget):
    """Manual angle control panel with integrated 3D viewer.

    Contains sliders/spinboxes for elevation and rotation,
    a button to send angle commands, and a 3D web viewer.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = LoggingService()
        self.validation_service = ValidationService()
        self._manual_syncing = False
        self._build_ui()
        self._connect_signals()
        self._sync_widgets(0, 0)

    def _build_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(18)

        main_layout.addWidget(self._build_controls_panel(), 1)
        main_layout.addWidget(self._build_3d_viewer_panel(), 2)
        main_layout.setStretch(0, 1)
        main_layout.setStretch(1, 2)

    def _build_controls_panel(self) -> QWidget:
        widget = QWidget()
        layout = QGridLayout(widget)

        # Elevation (vertical slider + spinbox)
        self.elev_slider = QSlider(Qt.Orientation.Vertical)
        self.elev_slider.setRange(0, 145)
        self.elev_spin = QSpinBox()
        self.elev_spin.setRange(0, 145)

        # Rotation (horizontal slider + spinbox)
        self.rot_slider = QSlider(Qt.Orientation.Horizontal)
        self.rot_slider.setRange(0, 360)
        self.rot_spin = QSpinBox()
        self.rot_spin.setRange(0, 360)

        # Send button
        cargar_btn = QPushButton("Cargar Orden")
        cargar_btn.setStyleSheet(
            "QPushButton { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f0f0f0, stop:1 #bcbec0); "
            "border: 2px outset #888; border-radius: 8px; color: #0a0; font: bold 15px Arial; "
            "min-width: 160px; min-height: 38px; } QPushButton:pressed { background: #e0e0e0; }"
        )

        layout.addWidget(QLabel("Elevacion"), 0, 0)
        layout.addWidget(self.elev_slider, 1, 0, 2, 1)
        layout.addWidget(self.elev_spin, 1, 1)
        layout.addWidget(QLabel("Rotacion"), 3, 0)
        layout.addWidget(self.rot_slider, 4, 0, 1, 2)
        layout.addWidget(self.rot_spin, 4, 2)
        layout.addWidget(cargar_btn, 5, 0, 1, 3)
        layout.setRowStretch(6, 1)

        widget.setMinimumWidth(220)
        return widget

    def _build_3d_viewer_panel(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.visor3d = QWebEngineView()

        try:
            from PyQt6.QtWebEngineCore import QWebEngineSettings

            self.visor3d.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        except Exception as e:
            self.logger.debug(f"No se pudo establecer LocalContentCanAccessRemoteUrls: {e}")

        visor_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "visor_3d_piranometro.html"))
        self.visor3d.load(QUrl.fromLocalFile(visor_path))
        self.visor3d.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.visor3d.setMinimumSize(0, 0)

        layout.addWidget(self.visor3d)
        return widget

    def _connect_signals(self) -> None:
        # Find the button and connect
        for child in self.children():
            if isinstance(child, QPushButton):
                child.clicked.connect(self._send_manual_command)
                break

        self.elev_slider.valueChanged.connect(self._on_angle_changed)
        self.elev_spin.valueChanged.connect(self._on_angle_changed)
        self.rot_slider.valueChanged.connect(self._on_angle_changed)
        self.rot_spin.valueChanged.connect(self._on_angle_changed)

    def setup_web_channel(self) -> QWebChannel:
        channel = QWebChannel(self.visor3d.page())
        self.visor3d.page().setWebChannel(channel)
        return channel

    def _on_angle_changed(self, value: int) -> None:
        if self._manual_syncing:
            return
        self._manual_syncing = True

        sender = self.sender()
        if sender == self.elev_slider:
            self.elev_spin.setValue(self.elev_slider.value())
        elif sender == self.elev_spin:
            self.elev_slider.setValue(self.elev_spin.value())
        elif sender == self.rot_slider:
            self.rot_spin.setValue(self.rot_slider.value())
        elif sender == self.rot_spin:
            self.rot_slider.setValue(self.rot_spin.value())

        self._manual_syncing = False

    def _sync_widgets(self, rot: int, ele: int) -> None:
        if self.rot_spin.value() != rot:
            self.rot_spin.setValue(rot)
        if self.rot_slider.value() != rot:
            self.rot_slider.setValue(rot)
        if self.elev_spin.value() != ele:
            self.elev_spin.setValue(ele)
        if self.elev_slider.value() != ele:
            self.elev_slider.setValue(ele)

    def _send_manual_command(self) -> None:
        rot = self.rot_spin.value()
        ele = self.elev_spin.value()

        rot_valid, rot_error = self.validation_service.validate_rotation(float(rot))
        ele_valid, ele_error = self.validation_service.validate_elevation(float(ele))

        if not rot_valid:
            QMessageBox.critical(self, "Error de Validacion", f"Angulo de rotacion invalido:\n{rot_error}")
            return
        if not ele_valid:
            QMessageBox.critical(self, "Error de Validacion", f"Angulo de elevacion invalido:\n{ele_error}")
            return

        self.logger.info(f"Sending manual angles: rotation={rot}, elevation={ele}")
        QMessageBox.information(self, "Consigna Enviada", f"Angulos ajustados manualmente:\nRotacion: {rot}\nElevacion: {ele}")

    def cleanup_3d_viewer(self) -> None:
        if hasattr(self, "visor3d"):
            try:
                self.visor3d.loadFinished.disconnect()
            except (TypeError, RuntimeError):
                pass
            self.visor3d.stop()
            self.visor3d.setHtml("")
            if self.visor3d.page():
                self.visor3d.page().deleteLater()
            self.visor3d.deleteLater()
            self.logger.debug("3D viewer resources released")
