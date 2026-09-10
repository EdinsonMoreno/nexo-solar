"""Location Setup Tab widget for Nexo Solar.

Provides location search, map display, coordinate management,
and solar information estimation for the equipment location.
"""

import requests
import webbrowser

from PyQt6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QPushButton,
    QFrame,
    QDoubleSpinBox,
    QLineEdit,
    QMessageBox,
    QTextBrowser,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont

from .map_widget import MapWidget
from ..data_access.logging_service import LoggingService


class LocationSetupTab(QWidget):
    """Tab for equipment location setup with search, map, and solar info.

    Signals:
        coordinates_applied: Emitted when coordinates are applied to solar tracking (lat, lon)
    """

    coordinates_applied = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = LoggingService()

        self._build_ui()
        self._update_location_info()

    def _build_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        left_panel = self._build_left_panel()
        right_panel = self._build_right_panel()

        main_layout.addLayout(left_panel, 2)
        main_layout.addLayout(right_panel, 3)

    def _build_left_panel(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(12)

        controls = self._build_controls_panel()
        info = self._build_info_panel()

        layout.addWidget(controls)
        layout.addWidget(info)
        layout.addStretch()
        return layout

    def _build_controls_panel(self) -> QFrame:
        panel = QFrame()
        panel.setStyleSheet("QFrame { background: #e6e6e6; border: 1px solid #888; border-radius: 5px; }")
        layout = QGridLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)

        search_label = QLabel("Buscar ubicacion:")
        search_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Ej: Ciudad de Mexico, Mexico")
        self.search_input.setStyleSheet("QLineEdit { padding: 5px; border: 1px solid #888; border-radius: 3px; }")
        self.search_input.returnPressed.connect(self._search_location)

        search_btn = QPushButton("Buscar")
        search_btn.setStyleSheet(
            "QPushButton { background: #4CAF50; color: white; border: none; padding: 5px 15px; "
            "border-radius: 3px; font: bold 10px Arial; } QPushButton:hover { background: #45a049; }"
        )
        search_btn.clicked.connect(self._search_location)

        coords_label = QLabel("Coordenadas seleccionadas:")
        coords_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))

        lat_label = QLabel("Latitud:")
        self.lat_display = QDoubleSpinBox()
        self.lat_display.setRange(-90, 90)
        self.lat_display.setDecimals(6)
        self.lat_display.setValue(19.4326)
        self.lat_display.valueChanged.connect(self._on_coordinates_changed)

        lon_label = QLabel("Longitud:")
        self.lon_display = QDoubleSpinBox()
        self.lon_display.setRange(-180, 180)
        self.lon_display.setDecimals(6)
        self.lon_display.setValue(-99.1332)
        self.lon_display.valueChanged.connect(self._on_coordinates_changed)

        use_coords_btn = QPushButton("Usar Coordenadas")
        use_coords_btn.setStyleSheet(
            "QPushButton { background: #2196F3; color: white; border: none; padding: 5px 15px; "
            "border-radius: 3px; font: bold 10px Arial; } QPushButton:hover { background: #1976D2; }"
        )
        use_coords_btn.clicked.connect(self._apply_coordinates)

        layout.addWidget(search_label, 0, 0)
        layout.addWidget(self.search_input, 0, 1, 1, 2)
        layout.addWidget(search_btn, 0, 3)
        layout.addWidget(coords_label, 1, 0, 1, 4)
        layout.addWidget(lat_label, 2, 0)
        layout.addWidget(self.lat_display, 2, 1)
        layout.addWidget(lon_label, 2, 2)
        layout.addWidget(self.lon_display, 2, 3)
        layout.addWidget(use_coords_btn, 3, 1, 1, 2)

        for widget in [search_label, coords_label, lat_label, lon_label]:
            widget.setStyleSheet("color: #000;")

        return panel

    def _build_info_panel(self) -> QFrame:
        panel = QFrame()
        panel.setStyleSheet("QFrame { background: #f0f0f0; border: 1px solid #888; border-radius: 5px; }")
        layout = QVBoxLayout(panel)

        title = QLabel("Informacion de Ubicacion")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #000;")

        self.location_info = QTextBrowser()
        self.location_info.setMaximumHeight(300)
        self.location_info.setStyleSheet("QTextBrowser { background: white; border: 1px solid #ccc; color: #000; }")

        buttons = QHBoxLayout()
        maps_btn = QPushButton("Abrir en Google Maps")
        maps_btn.setStyleSheet(
            "QPushButton { background: #FF9800; color: white; border: none; padding: 8px 15px; "
            "border-radius: 3px; font: bold 11px Arial; } QPushButton:hover { background: #F57C00; }"
        )
        maps_btn.clicked.connect(self._open_google_maps)

        earth_btn = QPushButton("Abrir en Google Earth")
        earth_btn.setStyleSheet(
            "QPushButton { background: #4CAF50; color: white; border: none; padding: 8px 15px; "
            "border-radius: 3px; font: bold 11px Arial; } QPushButton:hover { background: #45a049; }"
        )
        earth_btn.clicked.connect(self._open_google_earth)

        buttons.addWidget(maps_btn)
        buttons.addWidget(earth_btn)
        buttons.addStretch()

        layout.addWidget(title)
        layout.addWidget(self.location_info)
        layout.addLayout(buttons)
        return panel

    def _build_right_panel(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        self.map_widget = MapWidget(lat=self.lat_display.value(), lon=self.lon_display.value(), zoom=13)
        self.map_widget.setMinimumSize(500, 350)
        self.map_widget.location_selected.connect(self._on_map_location_selected)
        layout.addWidget(self.map_widget)

        self.lat_display.valueChanged.connect(self._update_map_from_ui)
        self.lon_display.valueChanged.connect(self._update_map_from_ui)
        return layout

    def _update_map_from_ui(self) -> None:
        lat = self.lat_display.value()
        lon = self.lon_display.value()
        self.map_widget.set_location(lat, lon)

    def _update_location_info(self) -> None:
        lat = self.lat_display.value()
        lon = self.lon_display.value()

        lat_hem = "Norte" if lat >= 0 else "Sur"
        lon_hem = "Este" if lon >= 0 else "Oeste"
        zona_horaria = int(lon / 15)
        zona_str = f"UTC+{zona_horaria}" if zona_horaria >= 0 else f"UTC{zona_horaria}"
        region = self._determine_region(lat, lon)

        info_html = (
            f'<div style="font-family: Arial, sans-serif; padding: 10px; color: #000;">'
            f'<h3 style="color: #000; margin-top: 0; text-align: center;">Ubicacion del Equipo</h3>'
            f'<table style="width: 100%; border-collapse: collapse; margin: 10px 0; color: #000;">'
            f'<tr style="background: #e3f2fd; color: #000;">'
            f'<td style="padding: 8px; font-weight: bold; border: 1px solid #ddd; color: #000;">Coordenadas</td>'
            f'<td style="padding: 8px; border: 1px solid #ddd; color: #000;">{lat:.6f}, {lon:.6f}</td></tr>'
            f'<tr style="background: #f5f5f5; color: #000;">'
            f'<td style="padding: 8px; font-weight: bold; border: 1px solid #ddd; color: #000;">Hemisferio</td>'
            f'<td style="padding: 8px; border: 1px solid #ddd; color: #000;">{lat_hem} / {lon_hem}</td></tr>'
            f'<tr style="background: #e3f2fd; color: #000;">'
            f'<td style="padding: 8px; font-weight: bold; border: 1px solid #ddd; color: #000;">Zona Horaria</td>'
            f'<td style="padding: 8px; border: 1px solid #ddd; color: #000;">{zona_str}</td></tr>'
            f'<tr style="background: #f5f5f5; color: #000;">'
            f'<td style="padding: 8px; font-weight: bold; border: 1px solid #ddd; color: #000;">Region</td>'
            f'<td style="padding: 8px; border: 1px solid #ddd; color: #000;">{region}</td></tr></table>'
            f'<div style="background: #e8f5e8; padding: 10px; border-left: 4px solid #4CAF50; '
            f'border-radius: 3px; margin: 10px 0; color: #000;">'
            f'<h4 style="color: #000; margin: 0 0 8px 0;">Informacion Solar</h4>'
            f'<ul style="margin: 5px 0; padding-left: 20px; color: #000;">'
            f"<li><strong>Irradiancia promedio:</strong> {self._estimate_irradiance(lat)} kWh/m2/dia</li>"
            f"<li><strong>Horas de sol:</strong> {self._estimate_sun_hours(lat)} horas/dia</li>"
            f"<li><strong>Mejor orientacion:</strong> {self._best_orientation(lat)}</li></ul></div>"
            f'<div style="background: #fff3cd; padding: 10px; border-left: 4px solid #ffc107; '
            f'border-radius: 3px; margin: 10px 0; color: #000;">'
            f"<strong>Recomendacion:</strong>"
            f'<p style="margin: 5px 0; color: #000;">Verifica la ubicacion usando los botones de mapas '
            f"para asegurar que no hay obstaculos (edificios, arboles) que puedan generar sombras.</p></div></div>"
        )
        self.location_info.setHtml(info_html)

    def _on_coordinates_changed(self) -> None:
        self._update_location_info()
        self._update_map_from_ui()

    def _on_map_location_selected(self, lat: float, lon: float) -> None:
        self.lat_display.setValue(lat)
        self.lon_display.setValue(lon)
        self._update_location_info()

    def _search_location(self) -> None:
        query = self.search_input.text().strip()
        if not query:
            QMessageBox.warning(self, "Busqueda", "Por favor ingrese una ubicacion para buscar.")
            return

        try:
            url = f"https://nominatim.openstreetmap.org/search?q={query}&format=json&limit=1"
            headers = {"User-Agent": "Nexo Solar/1.0"}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data:
                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])
                self.lat_display.setValue(lat)
                self.lon_display.setValue(lon)
                self._update_location_info()
                self._update_map_from_ui()
                QMessageBox.information(
                    self, "Busqueda exitosa", f"Ubicacion encontrada: {data[0].get('display_name', query)}"
                )
            else:
                QMessageBox.warning(self, "Busqueda", "No se encontro la ubicacion especificada.")
        except requests.RequestException as e:
            QMessageBox.critical(self, "Error de conexion", f"Error al buscar la ubicacion:\n{str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error inesperado:\n{str(e)}")

    def _apply_coordinates(self) -> None:
        lat = self.lat_display.value()
        lon = self.lon_display.value()
        self.coordinates_applied.emit(lat, lon)
        QMessageBox.information(
            self,
            "Coordenadas aplicadas",
            f"Las coordenadas han sido aplicadas al sistema de seguimiento solar:\n"
            f"Latitud: {lat:.6f}\nLongitud: {lon:.6f}",
        )

    def sync_from_calculation(self, lat: float, lon: float) -> None:
        self.lat_display.blockSignals(True)
        self.lon_display.blockSignals(True)
        self.lat_display.setValue(lat)
        self.lon_display.setValue(lon)
        self.lat_display.blockSignals(False)
        self.lon_display.blockSignals(False)
        self._update_location_info()
        self._update_map_from_ui()

    def _open_google_maps(self) -> None:
        lat = self.lat_display.value()
        lon = self.lon_display.value()
        try:
            webbrowser.open(f"https://www.google.com/maps?q={lat},{lon}&z=15")
            QMessageBox.information(self, "Google Maps", f"Abriendo Google Maps...\nUbicacion: {lat:.6f}, {lon:.6f}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir Google Maps:\n{str(e)}")

    def _open_google_earth(self) -> None:
        lat = self.lat_display.value()
        lon = self.lon_display.value()
        try:
            webbrowser.open(f"https://earth.google.com/web/@{lat},{lon},1000a,1000d,35y,0h,45t,0r")
            QMessageBox.information(self, "Google Earth", f"Abriendo Google Earth...\nUbicacion: {lat:.6f}, {lon:.6f}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir Google Earth:\n{str(e)}")

    @staticmethod
    def _determine_region(lat: float, lon: float) -> str:
        if -30 <= lat <= 30:
            return "Tropical"
        elif 30 < lat <= 60 or -60 <= lat < -30:
            return "Templada"
        return "Polar"

    @staticmethod
    def _estimate_irradiance(lat: float) -> str:
        abs_lat = abs(lat)
        if abs_lat <= 23.5:
            return "5.0-6.5"
        elif abs_lat <= 45:
            return "3.5-5.0"
        return "1.0-3.5"

    @staticmethod
    def _estimate_sun_hours(lat: float) -> str:
        abs_lat = abs(lat)
        if abs_lat <= 23.5:
            return "10-12"
        elif abs_lat <= 45:
            return "8-10"
        return "4-8"

    @staticmethod
    def _best_orientation(lat: float) -> str:
        return "Sur (Hemisferio Norte)" if lat >= 0 else "Norte (Hemisferio Sur)"
