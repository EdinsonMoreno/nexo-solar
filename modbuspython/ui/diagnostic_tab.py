from PyQt6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QGridLayout,
    QPushButton,
    QLineEdit,
    QTextEdit,
    QCheckBox,
    QMessageBox,
)


from PyQt6.QtGui import QFont, QPixmap, QColor


from PyQt6.QtCore import Qt, QTimer, QDateTime


from typing import Optional, Dict


from ..data_access.modbus_client import ModbusClient as ModbusManager
from ..config.config_defaults import DEFAULT_CONFIG


from ..backend.angle_state_manager import AngleStateManager


from ..backend.validation_service import ValidationService


from ..data_access.logging_service import LoggingService


import os


class DiagnosticTab(QWidget):

    def __init__(self, modbus_manager: Optional[ModbusManager] = None) -> None:

        super().__init__()

        self.logger: LoggingService = LoggingService()

        self.validation_service: ValidationService = ValidationService()

        self.leds: Dict[str, QLabel] = {}

        self.modbus: ModbusManager

        self.angle_manager: AngleStateManager

        self.update_count: int = 0

        self.timer: QTimer

        main_layout = QHBoxLayout(self)

        main_layout.setContentsMargins(20, 10, 20, 10)

        # Panel izquierdo (estado, conexión, controles)

        left_panel = QVBoxLayout()

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

            else:

                logo.setText("Nexo Solar")

                logo.setFont(QFont("Arial", 28, QFont.Weight.Bold))

        else:

            logo.setText("Nexo Solar")

            logo.setFont(QFont("Arial", 28, QFont.Weight.Bold))

        logo.setStyleSheet("background: transparent;")

        logo_row.addWidget(logo)

        logo_row.addStretch()

        left_panel.addLayout(logo_row)

        left_panel.addSpacing(10)

        # Panel de estado y controles

        panel = QFrame()

        panel.setStyleSheet("QFrame { background: #c0c2c4; border: 2px solid #888; border-radius: 8px; }")

        panel_layout = QGridLayout(panel)

        panel_layout.setHorizontalSpacing(40)

        panel_layout.setVerticalSpacing(30)

        estados = [
            ("Conexión", QColor(255, 0, 0)),
            ("Sensor", QColor(255, 0, 0)),
        ]

        self.leds = {}

        for i, (nombre, color) in enumerate(estados):

            label = QLabel(nombre)

            label.setFont(QFont("Arial", 14, QFont.Weight.Bold))

            label.setStyleSheet("color: #222;")

            led = QLabel()

            led.setFixedSize(32, 32)

            led.setStyleSheet(f"background: {color.name()}; border: 2px solid #888; border-radius: 16px;")

            panel_layout.addWidget(label, i, 0)

            panel_layout.addWidget(led, i, 1)

            self.leds[nombre] = led

        diag_btn = QPushButton("Diagnóstico Automático")

        diag_btn.setStyleSheet(
            "QPushButton { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f0f0f0, stop:1 #bcbec0); border: 2px outset #888; border-radius: 8px; color: #005fa3; font: bold 15px Arial; min-width: 220px; min-height: 38px; } QPushButton:pressed { background: #e0e0e0; }"
        )

        panel_layout.addWidget(diag_btn, len(estados), 0, 1, 2)

        left_panel.addWidget(panel, 0)

        # Panel de controles rápidos

        quick_panel = QFrame()

        quick_panel.setStyleSheet("QFrame { background: #e0e0e0; border: 2px solid #888; border-radius: 8px; }")

        quick_layout = QGridLayout(quick_panel)

        quick_layout.setHorizontalSpacing(18)

        quick_layout.setVerticalSpacing(10)

        quick_layout.addWidget(QLabel("IP ESP8266:"), 0, 0)

        self.ip_edit = QLineEdit(DEFAULT_CONFIG["modbus"]["host"])

        quick_layout.addWidget(self.ip_edit, 0, 1)

        quick_layout.addWidget(QLabel("Puerto:"), 0, 2)

        self.port_edit = QLineEdit("502")

        quick_layout.addWidget(self.port_edit, 0, 3)

        quick_layout.addWidget(QLabel("Motor 1 (°):"), 1, 0)

        self.motor1_val = QLineEdit("0")

        self.motor1_val.setReadOnly(True)

        quick_layout.addWidget(self.motor1_val, 1, 1)

        quick_layout.addWidget(QLabel("Motor 2 (°):"), 1, 2)

        self.motor2_val = QLineEdit("0")

        self.motor2_val.setReadOnly(True)

        quick_layout.addWidget(self.motor2_val, 1, 3)

        quick_layout.addWidget(QLabel("Radiación solar (W/m²):"), 2, 0)

        self.radiacion_label = QLabel("0")

        self.radiacion_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))

        quick_layout.addWidget(self.radiacion_label, 2, 1)

        self.connect_btn = QPushButton("Conectar")

        self.connect_btn.setStyleSheet("QPushButton { min-width: 120px; min-height: 32px; font: bold 13px Arial; }")

        self.connect_btn.clicked.connect(self.toggle_conexion)

        quick_layout.addWidget(self.connect_btn, 2, 2)

        # Safe state indicator and recovery button

        self.safe_state_label = QLabel("Estado: Normal")

        self.safe_state_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))

        self.safe_state_label.setStyleSheet("color: #00c800;")

        quick_layout.addWidget(self.safe_state_label, 3, 0, 1, 2)

        self.recovery_btn = QPushButton("Recuperar de Modo Seguro")

        self.recovery_btn.setStyleSheet(
            "QPushButton { min-width: 180px; min-height: 32px; font: bold 13px Arial; background: #ff9800; }"
        )

        self.recovery_btn.clicked.connect(self.exit_safe_state)

        self.recovery_btn.setVisible(False)  # Hidden by default

        quick_layout.addWidget(self.recovery_btn, 3, 2, 1, 2)

        left_panel.addWidget(quick_panel, 0)

        left_panel.addStretch()

        # Panel derecho (consola de logs y datos)

        right_panel = QVBoxLayout()

        diag_panel = QFrame()

        diag_panel.setStyleSheet("QFrame { background: #e0e0e0; border: 2px solid #888; border-radius: 8px; }")

        diag_layout = QGridLayout(diag_panel)

        diag_layout.setHorizontalSpacing(18)

        diag_layout.setVerticalSpacing(10)

        diag_layout.addWidget(QLabel("Consola de logs:"), 0, 0, 1, 4)

        self.log_text = QTextEdit()

        self.log_text.setReadOnly(True)

        self.log_text.setStyleSheet(
            "QTextEdit { background: #181818; color: #00FF00; font: 13px 'Courier New', monospace; border: none; border-radius: 0px; }"
        )

        diag_layout.addWidget(self.log_text, 1, 0, 1, 4)

        self.estado_label = QLabel("Desconectado")

        self.intensidad_label = QLabel("Timeout")

        diag_layout.addWidget(QLabel("Estado:"), 2, 0)

        diag_layout.addWidget(self.estado_label, 2, 1)

        diag_layout.addWidget(QLabel("Intensidad señal:"), 2, 2)

        diag_layout.addWidget(self.intensidad_label, 2, 3)

        self.leer_btn = QPushButton("Leer Radiación")

        self.leer_btn.clicked.connect(self.leer_radiacion)

        self.enviar_btn = QPushButton("Enviar Consignas")

        self.enviar_btn.clicked.connect(self.enviar_consignas)

        self.auto_check = QCheckBox("Lectura automática")

        self.auto_check.setChecked(True)

        self.auto_check.stateChanged.connect(self.toggle_auto)

        diag_layout.addWidget(self.leer_btn, 3, 0)

        diag_layout.addWidget(self.enviar_btn, 3, 1)

        diag_layout.addWidget(self.auto_check, 3, 2, 1, 2)

        self.valor_label = QLabel("0")

        self.quality_label = QLabel("Bad")

        self.timestamp_label = QLabel("-")

        self.update_count_label = QLabel("0")

        diag_layout.addWidget(QLabel("Valor:"), 4, 0)

        diag_layout.addWidget(self.valor_label, 4, 1)

        diag_layout.addWidget(QLabel("Quality:"), 4, 2)

        diag_layout.addWidget(self.quality_label, 4, 3)

        diag_layout.addWidget(QLabel("Timestamp:"), 5, 0)

        diag_layout.addWidget(self.timestamp_label, 5, 1)

        diag_layout.addWidget(QLabel("Update Count:"), 5, 2)

        diag_layout.addWidget(self.update_count_label, 5, 3)

        self.prueba_btn = QPushButton("Prueba Modbus")

        self.prueba_btn.clicked.connect(self.prueba_modbus)

        self.detener_btn = QPushButton("Detener Prueba")

        self.detener_btn.clicked.connect(self.detener_prueba)

        self.detener_btn.setEnabled(False)

        diag_layout.addWidget(self.prueba_btn, 6, 0, 1, 2)

        diag_layout.addWidget(self.detener_btn, 6, 2, 1, 2)

        right_panel.addWidget(diag_panel)

        main_layout.addLayout(left_panel, 2)

        main_layout.addLayout(right_panel, 3)

        # Backend - usar el ModbusManager compartido

        self.modbus = modbus_manager if modbus_manager else ModbusManager()

        self.modbus.radiacion_actualizada.connect(self.actualizar_radiacion)

        self.modbus.log.connect(self.agregar_log)

        self.modbus.conexion_cambiada.connect(self.actualizar_led_conexion)

        self.modbus.retry_exhausted.connect(self.on_retry_exhausted)

        self.angle_manager = AngleStateManager()

        self.angle_manager.angles_changed.connect(self._on_angles_updated)

        self.angle_manager.mode_changed.connect(self._on_mode_changed)

        self._on_angles_updated(*self.angle_manager.get_angles(), None)

        self._on_mode_changed(self.angle_manager.get_mode(), None)

        diag_btn.clicked.connect(self.diagnostico_automatico)

        self.update_count = 0

        self.timer = QTimer()

        self.timer.timeout.connect(self.simular_estados)

        self.timer.start(500)

        for i in range(diag_layout.count()):

            item = diag_layout.itemAt(i).widget()

            if isinstance(item, QLabel) or isinstance(item, QLineEdit):

                item.setStyleSheet(item.styleSheet() + "color: #000;")

        self.log_text.setStyleSheet(
            "QTextEdit { background: #181818; color: #00FF00; font: 13px 'Courier New', monospace; border: none; border-radius: 0px; }"
        )

    def actualizar_led_conexion(self, conectado: bool) -> None:

        # LED de Conexión: Verde si conectado, Rojo si desconectado

        color_conexion = "#00c800" if conectado else "#c80000"

        self.leds["Conexión"].setStyleSheet(f"background: {color_conexion}; border: 2px solid #888; border-radius: 16px;")

        # Actualizar botón y estado según conexión real

        if conectado:

            self.connect_btn.setText("Desconectar")

            self.estado_label.setText("Conectado")

        else:

            self.connect_btn.setText("Conectar")

            self.estado_label.setText("Desconectado")

        # LED de Sensor: actualizar según el estado de lectura

        self.actualizar_led_sensor()

    def actualizar_led_sensor(self) -> None:
        """Actualiza el LED del sensor según el estado:





        - Verde: leyendo datos automáticamente





        - Amarillo: conectado pero sin lectura automática





        - Rojo: sin conexión
        """

        if not self.modbus.is_connected:

            # Sin conexión - Rojo

            color_sensor = "#c80000"

        elif self.auto_check.isChecked() and self.modbus.timer is not None and self.modbus.timer.isActive():

            # Leyendo datos automáticamente - Verde

            color_sensor = "#00c800"

        else:

            # Conectado pero sin lectura automática - Amarillo

            color_sensor = "#ffcc00"

        self.leds["Sensor"].setStyleSheet(f"background: {color_sensor}; border: 2px solid #888; border-radius: 16px;")

    def diagnostico_automatico(self) -> None:

        # Ejecutar diagnóstico real de los componentes

        self.modbus.log.emit("Diagnóstico automático ejecutado")

        # Actualizar estados reales basados en la conexión actual

        self.actualizar_led_conexion(self.modbus.is_connected)

    def simular_estados(self) -> None:

        # Simulación periódica de estados (puede ser reemplazada por lógica real)

        self.actualizar_led_conexion(self.modbus.is_connected)

    def toggle_conexion(self) -> None:

        if self.connect_btn.text() == "Conectar":

            # Validar IP y puerto antes de conectar

            ip = self.ip_edit.text()

            port_text = self.port_edit.text()

            # Validar IP

            ip_valid, ip_error = self.validation_service.validate_ip_address(ip)

            if not ip_valid:

                QMessageBox.critical(self, "Error de Validación", f"Dirección IP inválida:\n{ip_error}")

                self.logger.error(f"Validation failed for IP address: {ip_error}")
                return

            # Validar puerto

            try:

                port = int(port_text)

            except ValueError:

                QMessageBox.critical(self, "Error de Validación", "Puerto inválido: debe ser un número entero")

                self.logger.error("Validation failed for port: not an integer")
                return

            port_valid, port_error = self.validation_service.validate_port(port)

            if not port_valid:

                QMessageBox.critical(self, "Error de Validación", f"Puerto inválido:\n{port_error}")

                self.logger.error(f"Validation failed for port: {port_error}")
                return

            # Si la validación pasa, conectar

            self.modbus.ip = ip

            self.modbus.port = port

            self.modbus.connect()

            self.connect_btn.setText("Desconectar")

            self.estado_label.setText("Conectado")

            self.logger.info(f"Connected to Modbus device at {ip}:{port}")

            # Solo iniciar lectura automática si está marcado el checkbox

            if self.auto_check.isChecked():

                self.modbus.start(2000)  # Cambiar a 2 segundos

        else:

            self.modbus.disconnect()  # Usar el nuevo método

            self.connect_btn.setText("Conectar")

            self.estado_label.setText("Desconectado")

            self.logger.info("Disconnected from Modbus device")

    def leer_radiacion(self) -> None:

        self.modbus.read_irradiance()

    def enviar_consignas(self) -> None:

        # Obtener valores actuales del manager

        rot, ele = self.angle_manager.get_angles()

        # Validar ángulos antes de enviar

        rot_valid, rot_error = self.validation_service.validate_rotation(float(rot))

        ele_valid, ele_error = self.validation_service.validate_elevation(float(ele))

        if not rot_valid:

            QMessageBox.critical(self, "Error de Validación", f"Ángulo de rotación inválido:\n{rot_error}")

            self.logger.error(f"Validation failed for rotation angle: {rot_error}")
            return

        if not ele_valid:

            QMessageBox.critical(self, "Error de Validación", f"Ángulo de elevación inválido:\n{ele_error}")

            self.logger.error(f"Validation failed for elevation angle: {ele_error}")
            return

        # Si la validación pasa, enviar consignas

        self.logger.info(f"Sending angles to Modbus: rotation={rot}°, elevation={ele}°")

        self.modbus.write_setpoints(rot, ele)

    def toggle_auto(self, state: int) -> None:

        if state and self.modbus.is_connected:

            # Solo iniciar si está conectado

            self.modbus.start(2000)  # Cambiar a 2 segundos

            self.agregar_log("Lectura automática iniciada")

        else:

            # Detener solo la lectura automática, no la conexión

            self.modbus.detener_lectura()

            if not state:

                self.agregar_log("Lectura automática detenida")

        # Actualizar el LED del sensor según el nuevo estado

        self.actualizar_led_sensor()

    def prueba_modbus(self) -> None:

        self.prueba_btn.setEnabled(False)

        self.detener_btn.setEnabled(True)

        self.log_text.append("Iniciando prueba Modbus...")

        # Enviar y recibir paquetes reales

        if self.modbus.is_connected:

            self.modbus.read_irradiance()

            self.modbus.log.emit("[Prueba Modbus] Paquete enviado y recibido correctamente")

        else:

            self.modbus.log.emit("[Prueba Modbus] Error: No conectado")

    def detener_prueba(self) -> None:

        self.prueba_btn.setEnabled(True)

        self.detener_btn.setEnabled(False)

        self.log_text.append("Prueba Modbus detenida.")

    def actualizar_radiacion(self, valor: float) -> None:

        # Mostrar valor con 2 decimales

        valor_formateado = f"{valor:.2f}"

        self.radiacion_label.setText(valor_formateado)

        self.valor_label.setText(valor_formateado)

        self.timestamp_label.setText(QDateTime.currentDateTime().toString("HH:mm:ss"))

        self.update_count += 1

        self.update_count_label.setText(str(self.update_count))

        # Quality

        self.quality_label.setText("Good" if valor > 0 else "Bad")

        # Actualizar LED del sensor cuando se reciben datos

        self.actualizar_led_sensor()

    def agregar_log(self, msg: str) -> None:

        self.log_text.append(msg)

    def _on_angles_updated(self, rot: float, ele: float, source: Optional[object] = None) -> None:

        # Sincronizar campos de la UI con el estado global

        if self.motor1_val.text() != str(rot):

            self.motor1_val.setText(str(rot))

        if self.motor2_val.text() != str(ele):

            self.motor2_val.setText(str(ele))

    def _on_mode_changed(self, mode: str, source: Optional[object] = None) -> None:

        # Aquí podrías actualizar la UI según el modo (manual/auto)

        # Ejemplo: mostrar el modo en un label o log

        if hasattr(self, "log_text"):

            self.log_text.append(f"[Modo] Cambiado a: {mode}")

    def on_retry_exhausted(self, operation: str, error_message: str) -> None:
        """





        Handler para la señal retry_exhausted del ModbusClient.





        Actualiza el indicador de safe state en la UI.






        Args:





            operation: Nombre de la operación que falló





            error_message: Mensaje de error detallado
        """

        self.logger.warning(f"Retry exhausted signal received for operation: {operation}")

        self.update_safe_state_indicator()

    def update_safe_state_indicator(self) -> None:
        """Actualiza el indicador visual de safe state."""

        if self.modbus.is_in_safe_state():

            self.safe_state_label.setText("⚠️ Estado: MODO SEGURO")

            self.safe_state_label.setStyleSheet("color: #ff0000; font-weight: bold;")

            self.recovery_btn.setVisible(True)

            self.agregar_log("[SISTEMA] Entrando en MODO SEGURO - Operaciones de escritura deshabilitadas")

        else:

            self.safe_state_label.setText("Estado: Normal")

            self.safe_state_label.setStyleSheet("color: #00c800; font-weight: bold;")

            self.recovery_btn.setVisible(False)

    def exit_safe_state(self) -> None:
        """Permite al usuario salir manualmente del modo seguro."""

        from PyQt6.QtWidgets import QMessageBox

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

            self.agregar_log("[SISTEMA] Saliendo del MODO SEGURO - Operaciones de escritura habilitadas")

            self.logger.info("User manually exited safe state")

    def cleanup(self) -> None:
        """Clean up resources (timers)."""

        from ..data_access.logging_service import LoggingService

        logger = LoggingService()

        logger.debug("DiagnosticTab cleanup: releasing resources")

        try:

            # Stop and delete the timer

            if hasattr(self, "timer"):

                self.timer.stop()

                self.timer.deleteLater()

                logger.debug("Diagnostic timer stopped and deleted")

        except Exception as e:

            logger.error(f"Error cleaning up timer: {e}")

        logger.info("DiagnosticTab cleanup completed")
