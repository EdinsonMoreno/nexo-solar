"""Solar Tracker Automatic Tab widget.

Calculates and displays solar angles (HRA, declination, elevation, azimuth)
based on latitude, longitude, day of year, and local time.
"""

import datetime

from PyQt6.QtWidgets import (
    QWidget,
    QLabel,
    QGridLayout,
    QDoubleSpinBox,
    QSpinBox,
    QLineEdit,
)

from ..backend.solar_calcs import calculate_hra, calculate_decl, calculate_alt, calculate_az
from ..data_access.logging_service import LoggingService


class SolarTrackerTab(QWidget):
    """Tab for automatic solar angle calculations.

    Inputs: latitude, longitude, day of year, local time.
    Outputs: HRA, declination, elevation, azimuth angles.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = LoggingService()
        self._build_ui()
        self._connect_signals()
        self._update_calculations()

    def _build_ui(self) -> None:
        layout = QGridLayout(self)
        layout.setHorizontalSpacing(40)
        layout.setVerticalSpacing(18)

        # Input widgets
        self.lat_spin = self._create_double_spin(-90, 90, 0.1, 6)
        self.lon_spin = self._create_double_spin(-180, 180, 0.1, 6)

        hoy = datetime.datetime.now()
        self.dia_spin = QSpinBox()
        self.dia_spin.setRange(1, 366)
        self.dia_spin.setValue(hoy.timetuple().tm_yday)

        self.hora_spin = QSpinBox()
        self.hora_spin.setRange(0, 24)
        self.hora_spin.setValue(hoy.hour)

        # Output widgets
        self.hra_val = QLineEdit("-180")
        self.hra_val.setReadOnly(True)
        self.dec_val = QLineEdit("-23.0116")
        self.dec_val.setReadOnly(True)
        self.alt_val = QLineEdit("-66.9884")
        self.alt_val.setReadOnly(True)
        self.az_val = QLineEdit("-0.00000000000001652")
        self.az_val.setReadOnly(True)

        # Add to layout
        layout.addWidget(QLabel("Latitud"), 0, 0)
        layout.addWidget(self.lat_spin, 0, 1)
        layout.addWidget(QLabel("Longitud"), 0, 2)
        layout.addWidget(self.lon_spin, 0, 3)
        layout.addWidget(QLabel("Dia del Ano"), 1, 0)
        layout.addWidget(self.dia_spin, 1, 1)
        layout.addWidget(QLabel("Tiempo Local"), 1, 2)
        layout.addWidget(self.hora_spin, 1, 3)
        layout.addWidget(QLabel("Angulo de Hora Solar (HRA)"), 2, 0)
        layout.addWidget(self.hra_val, 2, 1)
        layout.addWidget(QLabel("Declinacion Solar"), 2, 2)
        layout.addWidget(self.dec_val, 2, 3)
        layout.addWidget(QLabel("Angulo de Elevacion (ALT)"), 3, 0)
        layout.addWidget(self.alt_val, 3, 1)
        layout.addWidget(QLabel("Angulo de Azimut (AZ)"), 3, 2)
        layout.addWidget(self.az_val, 3, 3)

    @staticmethod
    def _create_double_spin(min_val: float, max_val: float, step: float, decimals: int) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(min_val, max_val)
        spin.setDecimals(decimals)
        spin.setSingleStep(step)
        return spin

    def _connect_signals(self) -> None:
        for w in [self.lat_spin, self.lon_spin, self.dia_spin, self.hora_spin]:
            w.valueChanged.connect(self._update_calculations)

    def _update_calculations(self) -> None:
        lat = self.lat_spin.value()
        lon = self.lon_spin.value()
        dia = self.dia_spin.value()
        hora = self.hora_spin.value()

        hra = calculate_hra(hora, lon, dia)
        decl = calculate_decl(dia)
        alt = calculate_alt(lat, decl, hra)
        az = calculate_az(lat, decl, hra, alt)

        self.hra_val.setText(f"{hra:.2f}")
        self.dec_val.setText(f"{decl:.4f}")
        self.alt_val.setText(f"{alt:.4f}")
        self.az_val.setText(f"{az:.4f}")
