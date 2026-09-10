from PyQt6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QPushButton,
    QMessageBox,
)


from PyQt6.QtGui import QFont, QPixmap, QPainter


from PyQt6.QtCore import Qt, QPointF


from ..data_access.modbus_client import ModbusClient as ModbusManager


from .circular_gauge import CircularGauge


from .sqlite_dialog import SQLiteConfigDialog


from PyQt6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis


from ..backend.angle_state_manager import AngleStateManager


import os


class MonitorTab(QWidget):

    def __init__(self, modbus_manager=None):

        super().__init__()

        self.setObjectName("MonitorTab")

        main_layout = QVBoxLayout(self)

        main_layout.setContentsMargins(20, 10, 20, 10)

        # Logo y encabezado

        logo_row = QHBoxLayout()

        logo = QLabel()

        logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../assets/Logo.png"))

        if os.path.exists(logo_path):

            pixmap = QPixmap(logo_path)

            if not pixmap.isNull():

                logo.setPixmap(
                    pixmap.scaled(220, 70, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                )

                logo.setStyleSheet("background: transparent;")

            else:

                logo.setText("Nexo Solar")

                logo.setFont(QFont("Arial", 28, QFont.Weight.Bold))

                logo.setStyleSheet("background: transparent; color: #000;")

        else:

            logo.setText("Nexo Solar")

            logo.setFont(QFont("Arial", 28, QFont.Weight.Bold))

            logo.setStyleSheet("background: transparent; color: #000;")

        logo_row.addWidget(logo)

        logo_row.addStretch()

        main_layout.addLayout(logo_row)

        main_layout.addSpacing(10)

        # Panel principal

        main_panel = QHBoxLayout()

        main_panel.setSpacing(18)

        # Panel Medidor

        medidor_frame = QFrame()

        medidor_frame.setStyleSheet("QFrame { background: #bcbec0; border: 2px solid #888; border-radius: 12px; }")

        medidor_frame.setFixedWidth(600)

        medidor_layout = QVBoxLayout(medidor_frame)

        medidor_layout.setContentsMargins(18, 12, 18, 12)

        medidor_label = QLabel("Irradiancia w/m^2")

        medidor_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))

        medidor_label.setStyleSheet("color: #444;")

        medidor_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        medidor_layout.addWidget(medidor_label)

        # Gauge circular personalizado (reemplaza QDial)

        self.gauge = CircularGauge()

        self.gauge.setRange(0, 2000)

        self.gauge.setValue(0)

        medidor_layout.addWidget(self.gauge, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Display grande

        self.valor_label = QLabel("0000")

        self.valor_label.setFont(QFont("Courier New", 44, QFont.Weight.Bold))

        self.valor_label.setStyleSheet(
            "color: #111; background: #f4f4f4; border: 2px solid #bbb; border-radius: 10px; padding: 12px;"
        )

        self.valor_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        medidor_layout.addWidget(self.valor_label)

        medidor_layout.addSpacing(10)

        medidor_layout.addStretch()

        main_panel.addWidget(medidor_frame)

        # Panel Gráfico

        graf_frame = QFrame()

        graf_frame.setStyleSheet("QFrame { background: #bcbec0; border: 2px solid #888; border-radius: 12px; }")

        graf_layout = QVBoxLayout(graf_frame)

        graf_layout.setContentsMargins(12, 12, 12, 12)

        # Label superior

        graf_label_row = QHBoxLayout()

        graf_label = QLabel("Radiación Solar (W/m²)")

        graf_label.setFont(QFont("Arial", 11))

        graf_label.setStyleSheet("color: #bbb; background: transparent;")

        graf_label_row.addStretch()

        graf_label_row.addWidget(graf_label)

        graf_layout.addLayout(graf_label_row)

        # Gráfico de líneas en tiempo real

        self.series = QLineSeries()

        self.chart = QChart()

        self.chart.addSeries(self.series)

        self.chart.legend().hide()

        self.chart.setBackgroundBrush(Qt.GlobalColor.black)

        self.axis_x = QValueAxis()

        self.axis_x.setLabelFormat("%d")

        self.axis_x.setTitleText("Muestra")

        self.axis_x.setRange(0, 50)

        self.axis_y = QValueAxis()

        self.axis_y.setLabelFormat("%d")

        self.axis_y.setTitleText("W/m²")

        self.axis_y.setRange(0, 2000)

        self.chart.addAxis(self.axis_x, Qt.AlignmentFlag.AlignBottom)

        self.chart.addAxis(self.axis_y, Qt.AlignmentFlag.AlignLeft)

        self.series.attachAxis(self.axis_x)

        self.series.attachAxis(self.axis_y)

        self.chart_view = QChartView(self.chart)

        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)

        self.chart_view.setMinimumSize(420, 320)

        graf_layout.addWidget(self.chart_view, alignment=Qt.AlignmentFlag.AlignHCenter)

        graf_layout.addSpacing(10)

        main_panel.addWidget(graf_frame)

        main_layout.addLayout(main_panel)

        # Log visual

        from PyQt6.QtWidgets import QTextEdit

        self.log_text = QTextEdit()

        self.log_text.setReadOnly(True)

        self.log_text.setStyleSheet(
            "QTextEdit { background: #181818; color: #00ff00; font: 13px 'Courier New', monospace; border: none; border-radius: 0px; }"
        )

        self.log_text.setFixedHeight(110)

        main_layout.addSpacing(8)

        main_layout.addWidget(self.log_text)

        # Botón de configuración SQLite y estado del sistema

        sqlite_layout = QHBoxLayout()

        # Safe state indicator

        self.safe_state_label = QLabel("Estado: Normal")

        self.safe_state_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))

        self.safe_state_label.setStyleSheet("color: #00c800;")

        sqlite_layout.addWidget(self.safe_state_label)

        # Recovery button

        self.recovery_btn = QPushButton("🔄 Recuperar de Modo Seguro")

        self.recovery_btn.setStyleSheet("""


            QPushButton {


                background: #ff9800;


                color: white;


                border: 2px solid #ff6f00;


                border-radius: 8px;


                padding: 8px 16px;


                font-weight: bold;


                font-size: 12px;


            }


            QPushButton:hover {


                background: #ff6f00;


                border-color: #e65100;


            }


            QPushButton:pressed {


                background: #e65100;


            }
        """)

        self.recovery_btn.clicked.connect(self.exit_safe_state)

        self.recovery_btn.setVisible(False)  # Hidden by default

        sqlite_layout.addWidget(self.recovery_btn)

        sqlite_layout.addStretch()

        self.btn_configurar_sqlite = QPushButton("📊 Configurar Base de Datos SQLite")

        self.btn_configurar_sqlite.setStyleSheet("""


            QPushButton {


                background: #4a6741;


                color: white;


                border: 2px solid #5a7751;


                border-radius: 8px;


                padding: 8px 16px;


                font-weight: bold;


                font-size: 12px;


            }


            QPushButton:hover {


                background: #5a7751;


                border-color: #6a8761;


            }


            QPushButton:pressed {


                background: #3a5731;


            }
        """)

        self.btn_configurar_sqlite.clicked.connect(self.abrir_configuracion_sqlite)

        sqlite_layout.addWidget(self.btn_configurar_sqlite)

        sqlite_layout.addStretch()

        main_layout.addLayout(sqlite_layout)

        main_layout.addSpacing(8)

        # Integración del backend ModbusManager

        # Usar el ModbusManager compartido si se pasa, si no, crear uno (solo para pruebas)

        self.modbus = modbus_manager if modbus_manager else ModbusManager()

        self.modbus.radiacion_actualizada.connect(self.update_irradiance)
        self.modbus.log.connect(self.add_log)

        self.modbus.retry_exhausted.connect(self.on_retry_exhausted)

        # Buffer para los últimos N valores de radiación

        self.radiacion_buffer = []

        self.max_buffer = 50

        # Integración con AngleStateManager

        self.angle_manager = AngleStateManager()

        self.angle_manager.angles_changed.connect(self._on_angles_updated)

        self.angle_manager.mode_changed.connect(self._on_mode_changed)

        # Inicializar visualización con el estado global

        self._on_angles_updated(*self.angle_manager.get_angles(), None)

        self._on_mode_changed(self.angle_manager.get_mode(), None)

    def update_irradiance(self, valor):

        # El gauge está configurado para 0-2000 W/m², usar valor directamente

        valor_gauge = min(float(valor), 2000.0)  # Asegurar float y limitar

        self.gauge.setValue(valor_gauge)  # <--- USAR self.gauge

        # Mostrar valor con 2 decimales en el display

        valor_formateado = f"{valor:.2f}"

        self.valor_label.setText(valor_formateado)

        # Actualizar buffer y gráfica

        self.radiacion_buffer.append(float(valor))

        if len(self.radiacion_buffer) > self.max_buffer:

            self.radiacion_buffer.pop(0)

        puntos = [QPointF(i, v) for i, v in enumerate(self.radiacion_buffer)]

        self.series.replace(puntos)

        self.axis_x.setRange(0, max(self.max_buffer - 1, len(self.radiacion_buffer) - 1))

    def add_log(self, msg):

        self.log_text.append(msg)

    def abrir_configuracion_sqlite(self):
        """Abre el diálogo de configuración SQLite"""

        dialog = SQLiteConfigDialog(self)

        dialog.configuracion_aceptada.connect(self.configurar_sqlite)

        dialog.exec()

    def configurar_sqlite(self, ruta_db: str, nombre_tabla: str):
        """Configura SQLite en el ModbusManager"""

        try:

            exito = self.modbus.configurar_sqlite(ruta_db, nombre_tabla)

            if exito:

                QMessageBox.information(
                    self,
                    "SQLite Configurado",
                    f"Base de datos configurada correctamente:\n"
                    f"Archivo: {ruta_db}\n"
                    f"Tabla: {nombre_tabla}\n\n"
                    f"Los datos de irradiancia se guardarán automáticamente.",
                )

            else:

                QMessageBox.warning(
                    self,
                    "Error de Configuración",
                    "No se pudo configurar la base de datos SQLite. " "Revise el log para más detalles.",
                )

        except Exception as e:

            QMessageBox.critical(self, "Error", f"Error configurando SQLite: {e}")

    def _on_angles_updated(self, rot, ele, source=None):

        # Aquí podrías mostrar los ángulos en un label, log o widget si lo deseas

        # Por ejemplo, agregar al log:

        self.add_log(f"Ángulos actualizados: Rotación={rot}°, Elevación={ele}°")

    def _on_mode_changed(self, mode, source=None):

        # Aquí podrías actualizar la UI según el modo (manual/auto)

        self.add_log(f"Modo de operación cambiado a: {mode}")

    def on_retry_exhausted(self, operation: str, error_message: str):
        """


        Handler para la señal retry_exhausted del ModbusClient.


        Actualiza el indicador de safe state en la UI.



        Args:


            operation: Nombre de la operación que falló


            error_message: Mensaje de error detallado
        """

        from ..data_access.logging_service import LoggingService

        logger = LoggingService()

        logger.warning(f"Retry exhausted signal received for operation: {operation}")

        self.update_safe_state_indicator()

    def update_safe_state_indicator(self):
        """Actualiza el indicador visual de safe state."""

        if self.modbus.is_in_safe_state():

            self.safe_state_label.setText("⚠️ Estado: MODO SEGURO")

            self.safe_state_label.setStyleSheet("color: #ff0000; font-weight: bold;")

            self.recovery_btn.setVisible(True)

            self.add_log("[SISTEMA] Entrando en MODO SEGURO - Operaciones de escritura deshabilitadas")

        else:

            self.safe_state_label.setText("Estado: Normal")

            self.safe_state_label.setStyleSheet("color: #00c800; font-weight: bold;")

            self.recovery_btn.setVisible(False)

    def exit_safe_state(self):
        """Permite al usuario salir manualmente del modo seguro."""

        from PyQt6.QtWidgets import QMessageBox

        from ..data_access.logging_service import LoggingService

        reply = QMessageBox.question(
            self,
            "Recuperar de Modo Seguro",
            "¿Está seguro de que desea salir del modo seguro?\n\n"
            "Asegúrese de que el problema de conexión se ha resuelto antes de continuar.\n"
            "Las operaciones de escritura se reanudarán después de la recuperación.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:

            self.modbus.exit_safe_state()

            self.update_safe_state_indicator()

            self.add_log("[SISTEMA] Saliendo del MODO SEGURO - Operaciones de escritura habilitadas")

            logger = LoggingService()

            logger.info("User manually exited safe state from MonitorTab")
