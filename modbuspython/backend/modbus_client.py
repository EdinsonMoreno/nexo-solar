# Módulo de gestión de conexión y comunicación Modbus TCP para SolarSense.


# Incluye integración con PyQt6 para señales y temporización, y soporte para almacenamiento en SQLite.


from PyQt6.QtCore import QObject, pyqtSignal, QTimer


from pymodbus.client import ModbusTcpClient

from datetime import datetime


from typing import Optional, Tuple


import sqlite3


from . import sqlite_manager


from .angle_state_manager import AngleStateManager


from ..data_access.logging_service import LoggingService


class ModbusManager(QObject):

    # Señales para actualizar la UI y otros componentes

    radiacion_actualizada = pyqtSignal(float)  # Señal para nueva medición de radiación

    log = pyqtSignal(str)  # Señal para mensajes de log

    conexion_cambiada = pyqtSignal(bool)  # Señal para cambios de estado de conexión

    def __init__(self, ip: str = "192.168.1.100", port: int = 502, parent: Optional[QObject] = None) -> None:

        # Inicializa el gestor Modbus y recursos asociados

        self.logger = LoggingService()

        self.logger.debug("Initializing ModbusManager")

        super().__init__(parent)

        self.ip: str = ip

        self.port: int = port

        self.client: Optional[ModbusTcpClient] = None

        self.timer: QTimer = QTimer()
        self.timer.timeout.connect(self.leer_radiacion)

        self.is_connected: bool = False

        self.reg_radiacion: int = 0  # Usar registro 0 según configuración del ESP8266

        self.reg_motor1: int = 1

        self.reg_motor2: int = 2

        self.slave_id: int = 1

        self.logger.debug("Basic variables initialized")

        # Configuración SQLite

        self.sqlite_conn: Optional[sqlite3.Connection] = None

        self.tabla_sqlite: Optional[str] = None

        self.logger.debug("SQLite configuration initialized")

        # --- INTEGRACIÓN AngleStateManager ---

        try:

            from backend.angle_state_manager import AngleStateManager

            self.logger.debug("Importing AngleStateManager")

            self.angle_manager: AngleStateManager = AngleStateManager()

            self.angle_manager.angles_changed.connect(self._on_angles_changed)

            self.logger.debug("AngleStateManager connected successfully")

        except Exception as e:

            self.logger.error(f"Failed to initialize AngleStateManager: {e}")

        self.logger.debug("ModbusManager initialization completed")

    def conectar(self) -> None:

        # Intenta conectar al servidor Modbus TCP. Si falla, emite señal y loguea el error.

        try:

            self.logger.debug(f"Attempting Modbus connection to {self.ip}:{self.port}")

            self.log.emit(f"[DEBUG] Intentando conectar a {self.ip}:{self.port}")

            self.client = ModbusTcpClient(self.ip, port=self.port)

            tcp_ok = self.client.connect()

            self.is_connected = tcp_ok

            if self.is_connected:

                self.logger.info(f"Modbus connection established: {self.ip}:{self.port}")

                self.log.emit(f"Conectado a Modbus TCP: {self.ip}:{self.port}")

            else:

                self.logger.warning(f"Failed to establish Modbus connection to {self.ip}:{self.port}")

                self.log.emit(f"No se pudo establecer comunicación Modbus con {self.ip}:{self.port}")

            self.conexion_cambiada.emit(self.is_connected)

        except Exception as e:

            self.logger.error(f"Modbus connection error to {self.ip}:{self.port}: {e}")

            self.log.emit(f"Error de conexión Modbus: {e}")

            self.is_connected = False

            self.conexion_cambiada.emit(False)

    def iniciar(self, intervalo_ms: int = 1000) -> None:

        # Inicia la lectura periódica de radiación si la conexión está activa

        if self.is_connected:

            self.timer.start(intervalo_ms)

            self.logger.info(f"Automatic reading started every {intervalo_ms}ms")

            self.log.emit(f"Lectura automática iniciada cada {intervalo_ms}ms")

        else:

            self.logger.warning("Cannot start automatic reading: not connected to Modbus")

    def detener_lectura(self) -> None:

        # Detiene solo la lectura automática, mantiene la conexión

        self.timer.stop()

        self.logger.info("Automatic reading stopped")

        self.log.emit("Lectura automática detenida")

    def desconectar(self) -> None:

        # Desconecta completamente del servidor Modbus

        self.timer.stop()

        if self.client:
            self.client.close()

        self.is_connected = False

        self.conexion_cambiada.emit(False)

        self.logger.info("Disconnected from Modbus server")

        self.log.emit("Desconectado del servidor Modbus")

    def detener(self) -> None:

        # Legacy method - maintain compatibility
        self.desconectar()

    def leer_radiacion(self) -> None:

        # Realiza la lectura de radiación solar desde el registro Modbus

        if not self.is_connected:

            self.logger.warning("Cannot read radiation: not connected to Modbus")

            self.log.emit("No conectado a Modbus para leer radiación")
            return

        try:

            self.logger.debug(f"Reading input register {self.reg_radiacion} from {self.ip}:{self.port}")

            self.log.emit(f"[DEBUG] Leyendo input register {self.reg_radiacion} en {self.ip}:{self.port}")

            rr = self.client.read_input_registers(address=self.reg_radiacion, count=1)

            self.logger.debug(f"Modbus read response: {rr}")

            self.log.emit(f"[DEBUG] Respuesta lectura: {rr}")

            if rr is not None and hasattr(rr, "registers") and rr.registers:

                valor_raw = rr.registers[0]

                # Convertir valor raw a W/m² dividiendo por 100 (igual que en Arduino)

                valor_convertido = valor_raw / 100.0

                # Guardar en SQLite si está configurado

                self._guardar_en_sqlite(valor_convertido)

                self.radiacion_actualizada.emit(valor_convertido)

                self.logger.debug(f"Solar radiation read: {valor_convertido:.2f} W/m² (raw: {valor_raw})")

                self.log.emit(f"Radiación solar: {valor_convertido:.2f} W/m² (raw: {valor_raw})")

            else:

                self.logger.warning("Failed to read radiation: no response from device")

                self.log.emit("No se pudo leer radiación (sin respuesta)")

        except Exception as e:

            self.logger.error(f"Modbus read error: {e}")

            self.log.emit(f"Error de lectura Modbus: {e}")

            self.is_connected = False

            self.conexion_cambiada.emit(False)

    def _validate_angles(self, rot: float, ele: float) -> Tuple[int, int]:

        # Valida y normaliza los ángulos recibidos antes de enviarlos por Modbus.

        # - Rango rotación: 0-360

        # - Rango elevación: 0-145

        try:

            rot_int = int(round(float(rot)))

        except Exception:

            rot_int = 0

        try:

            ele_int = int(round(float(ele)))

        except Exception:

            ele_int = 0

        rot_int = max(0, min(360, rot_int))

        ele_int = max(0, min(145, ele_int))

        return rot_int, ele_int

    def escribir_consignas(self, motor1: float, motor2: float) -> None:

        # Envía las consignas de ángulo al ESP8266 vía Modbus TCP.

        # Solo se ejecuta si la conexión está activa.

        # Los valores se validan y se loguea el proceso para trazabilidad.

        if not self.is_connected:

            self.logger.warning("Cannot write setpoints: not connected to Modbus")

            self.log.emit("No conectado a Modbus para escribir consignas")
            return

        rot_int, ele_int = self._validate_angles(motor1, motor2)

        self.logger.debug(f"Preparing to write setpoints: Rotation={rot_int}, Elevation={ele_int}")

        self.log.emit(f"[DEBUG] Preparando envío de consignas: Rotación={rot_int}, Elevación={ele_int}")

        try:

            res1 = self.client.write_register(address=self.reg_motor1, value=rot_int)

            res2 = self.client.write_register(address=self.reg_motor2, value=ele_int)

            if (res1 and not res1.isError()) and (res2 and not res2.isError()):

                self.logger.debug(f"Setpoints written successfully: Motor1={rot_int}, Motor2={ele_int}")

                self.log.emit(f"Consignas enviadas correctamente: Motor1={rot_int}, Motor2={ele_int}")

            else:

                self.logger.error(f"Failed to write setpoints: {res1}, {res2}")

                self.log.emit(f"Error al escribir consignas: {res1}, {res2}")

        except Exception as e:

            self.logger.error(f"Error writing setpoints: {e}")

            self.log.emit(f"Error al escribir consignas: {e}")

    def configurar_sqlite(self, ruta_db: str, tabla: str) -> bool:

        # Configura la conexión SQLite para guardar datos automáticamente

        try:

            # Cerrar conexión anterior si existe

            if self.sqlite_conn:

                self.sqlite_conn.close()

            # Conectar a la nueva base de datos

            self.sqlite_conn = sqlite_manager.conectar_db(ruta_db)

            self.tabla_sqlite = tabla

            # Verificar que la tabla existe o crearla

            tablas_existentes = sqlite_manager.get_tables(self.sqlite_conn)

            if tabla not in tablas_existentes:

                sqlite_manager.crear_tabla(self.sqlite_conn, tabla)

                self.logger.info(f"SQLite table '{tabla}' created in database")

                self.log.emit(f"Tabla '{tabla}' creada en base de datos SQLite")

            self.logger.info(f"SQLite configured: {ruta_db} -> table '{tabla}'")

            self.log.emit(f"SQLite configurado: {ruta_db} -> tabla '{tabla}'")

            return True

        except Exception as e:

            self.logger.error(f"Error configuring SQLite: {e}")

            self.log.emit(f"Error configurando SQLite: {e}")

            self.sqlite_conn = None

            self.tabla_sqlite = None

            return False

    def _guardar_en_sqlite(self, irradiancia: float) -> None:

        # Guarda un registro de irradiancia en SQLite si está configurado

        if self.sqlite_conn is None or self.tabla_sqlite is None:
            return

        try:

            ahora = datetime.now()

            fecha = ahora.strftime("%Y-%m-%d")

            hora = ahora.strftime("%H:%M:%S")

            sqlite_manager.insert_record(self.sqlite_conn, self.tabla_sqlite, fecha, hora, irradiancia)

            self.logger.debug(f"Radiation data saved to SQLite: {irradiancia:.2f} W/m²")

        except Exception as e:

            self.logger.error(f"Error saving to SQLite: {e}")

            self.log.emit(f"Error guardando en SQLite: {e}")

    def _on_angles_changed(self, rot: float, ele: float, source: Optional[object] = None) -> None:

        # Slot conectado a AngleStateManager.angles_changed.

        # Solo envía consignas si el modo es válido y no es una prueba.

        # Separa el flujo de pruebas del flujo real.

        rot_int = int(round(rot))

        ele_int = int(round(ele))

        rot_int = max(0, min(360, rot_int))

        ele_int = max(0, min(145, ele_int))

        if self.is_connected and hasattr(self, "angle_manager"):

            modo = self.angle_manager.get_mode()

            if modo in ("auto", "manual") and source != "prueba":

                self.logger.debug(f"Angles changed, sending setpoints: rot={rot_int}, ele={ele_int}, mode={modo}")

                self.escribir_consignas(rot_int, ele_int)
