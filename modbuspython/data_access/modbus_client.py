"""Modbus TCP client for SolarSense SCADA.

This module provides a threaded Modbus TCP client that executes I/O operations
in a separate thread to keep the UI responsive. It handles connection management,
data reading/writing, retry logic, and integration with the angle state manager.

Requirements validated: 4.1, 4.2, 4.3, 4.9, 6.1, 6.2, 6.6, 6.8
"""

from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal, QTimer

from pymodbus.client import ModbusTcpClient

import sqlite3

from ..backend import sqlite_manager
from ..backend.angle_state_manager import AngleStateManager
from ..config.config_defaults import DEFAULT_CONFIG
from .logging_service import LoggingService
from .modbus_connection import ModbusConnector
from .modbus_reader import ModbusReader
from .modbus_writer import ModbusWriter


class ModbusClient(QThread):
    """Threaded Modbus TCP client for non-blocking I/O operations.

    This class inherits from QThread to execute all Modbus I/O operations in a
    separate thread, keeping the UI responsive. It provides automatic retry logic,
    connection management, and integration with the angle state manager.

    Signals:
        radiacion_actualizada (float): Emitted when new irradiance measurement is received
        log (str): Emitted for log messages
        conexion_cambiada (bool): Emitted when connection state changes
        retry_exhausted (str, str): Emitted when retry limit is exceeded (operation, error_message)

    Attributes:
        ip (str): Modbus server IP address
        port (int): Modbus server TCP port
        is_connected (bool): Current connection state
        safe_state (bool): Flag indicating system is in safe state after critical errors

    Requirements validated: 4.1, 4.2, 4.3, 4.9, 6.1, 6.2, 6.6, 6.8
    """

    radiacion_actualizada = pyqtSignal(float)
    log = pyqtSignal(str)
    conexion_cambiada = pyqtSignal(bool)
    retry_exhausted = pyqtSignal(str, str)

    def __init__(
        self,
        ip: str = DEFAULT_CONFIG["modbus"]["host"],
        port: int = DEFAULT_CONFIG["modbus"]["port"],
        parent=None,
        config_manager=None,
    ) -> None:
        """Initialize the Modbus client and associated resources.

        Args:
            ip: Modbus server IP address (default: from config_defaults)
            port: Modbus server TCP port (default: 502)
            parent: Qt parent widget (optional)
            config_manager: ConfigurationManager instance for loading retry settings (optional)

        Raises:
            Exception: If AngleStateManager initialization fails
        """
        super().__init__(parent)
        self.logger = LoggingService()
        self.logger.debug("Initializing ModbusClient")

        self.ip = ip
        self.port = port
        self.is_connected = False
        self.is_running = False
        self.safe_state = False

        self.reg_radiacion = 0
        self.reg_motor1 = 1
        self.reg_motor2 = 2
        self.slave_id = 1

        self.sqlite_conn: Optional[sqlite3.Connection] = None
        self.tabla_sqlite: Optional[str] = None
        self.logger.debug("SQLite configuration initialized")

        self.timer: Optional[QTimer] = None
        self.intervalo_lectura = 1000

        if config_manager:
            retry_attempts = config_manager.get("modbus.retry_attempts", 3)
            retry_backoff = config_manager.get("modbus.retry_backoff", 1.0)
            timeout = config_manager.get("modbus.timeout", 5.0)
        else:
            retry_attempts = 3
            retry_backoff = 1.0
            timeout = 5.0

        from .retry_strategy import RetryStrategy

        self.retry_strategy = RetryStrategy(
            max_attempts=retry_attempts,
            initial_delay=retry_backoff,
            backoff_factor=2.0,
            max_delay=30.0,
        )
        self.timeout = timeout
        self.logger.debug(f"RetryStrategy initialized: max_attempts={retry_attempts}, initial_delay={retry_backoff}s")

        self._client: Optional[ModbusTcpClient] = None

        self._connector = ModbusConnector(
            ip=ip,
            port=port,
            timeout=timeout,
            retry_strategy=self.retry_strategy,
            logger=self.logger,
            log_signal=self.log,
            connection_signal=self.conexion_cambiada,
            retry_exhausted_signal=self.retry_exhausted,
        )

        self._reader = ModbusReader(
            client=self,
            ip=ip,
            port=port,
            register_address=self.reg_radiacion,
            retry_strategy=self.retry_strategy,
            logger=self.logger,
            log_signal=self.log,
            radiation_signal=self.radiacion_actualizada,
            connection_signal=self.conexion_cambiada,
            retry_exhausted_signal=self.retry_exhausted,
        )

        self._writer = ModbusWriter(
            client=self,
            ip=ip,
            port=port,
            reg_motor1=self.reg_motor1,
            reg_motor2=self.reg_motor2,
            retry_strategy=self.retry_strategy,
            logger=self.logger,
            log_signal=self.log,
            connection_signal=self.conexion_cambiada,
            retry_exhausted_signal=self.retry_exhausted,
        )

        try:
            self.angle_manager: Optional[AngleStateManager] = AngleStateManager()
            self.angle_manager.angles_changed.connect(self._on_angles_changed)
            self.logger.debug("AngleStateManager connected successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize AngleStateManager: {e}")
            self.angle_manager = None

        self.logger.debug("ModbusClient initialization completed")

    @property
    def client(self) -> Optional[ModbusTcpClient]:
        """Get the underlying Modbus TCP client."""
        return self._client

    @client.setter
    def client(self, value: Optional[ModbusTcpClient]) -> None:
        """Set the underlying Modbus TCP client."""
        self._client = value

    def run(self) -> None:
        """Main thread loop for executing Modbus I/O operations.

        This method is automatically called when start() is invoked on the thread.
        It creates the timer in the thread context, attempts initial connection,
        and starts the event loop.

        Requirements validated: 6.1, 6.2
        """
        self.logger.info("ModbusClient thread started")
        self.is_running = True

        self.timer = QTimer()
        self.timer.timeout.connect(self.read_irradiance)

        self.connect()
        self.exec()
        self.logger.info("ModbusClient thread finished")

    def stop(self) -> None:
        """Stop the thread gracefully with 10-second timeout.

        Closes Modbus connection and cleans up resources before terminating.
        Ensures proper resource cleanup to prevent memory leaks.

        Requirements validated: 10.2, 10.3, 10.9
        """
        self.logger.info("Stopping ModbusClient thread - initiating graceful shutdown")
        self.is_running = False

        if self.timer:
            try:
                self.timer.stop()
                self.logger.debug("Timer stopped successfully")
            except Exception as e:
                self.logger.error(f"Error stopping timer: {e}")

        try:
            if self._client and self.is_connected:
                self.logger.debug("Closing Modbus connection")
                self._client.close()
                self.is_connected = False
                self.logger.info("Modbus connection closed successfully")
        except Exception as e:
            self.logger.error(f"Error closing Modbus connection: {e}")

        if self.sqlite_conn:
            try:
                self.sqlite_conn.close()
                self.logger.debug("SQLite connection closed")
            except Exception as e:
                self.logger.error(f"Error closing SQLite connection: {e}")

        self.quit()

        if not self.wait(10000):
            self.logger.warning("Thread did not finish within 10 second timeout, forcing termination")
            self.terminate()
            if not self.wait(1000):
                self.logger.error("Thread could not be terminated gracefully")
        else:
            self.logger.info("ModbusClient thread stopped gracefully")

        self.logger.info("ModbusClient shutdown complete")

    def connect(self) -> None:
        """Attempt to connect to Modbus TCP server with retry logic.

        Raises:
            ModbusConnectionError: If connection fails after all retry attempts
        """
        self._connector.client = self._client
        self._connector.connect()
        self._client = self._connector.client
        self.is_connected = self._connector.is_connected
        self.safe_state = self._connector.safe_state

    def disconnect(self) -> None:
        """Disconnect completely from Modbus server."""
        if self.timer:
            self.timer.stop()
        if self._client:
            self._client.close()
        self.is_connected = False
        self.conexion_cambiada.emit(False)
        self.logger.info("Disconnected from Modbus server")
        self.log.emit("Desconectado del servidor Modbus")

    def stop_all(self) -> None:
        """Legacy method - maintained for backward compatibility."""
        self.disconnect()

    def iniciar(self, intervalo_ms: int = 1000) -> None:
        """Start periodic irradiance reading if connection is active.

        Args:
            intervalo_ms: Reading interval in milliseconds (default: 1000)
        """
        if self.is_connected and self.timer:
            self.intervalo_lectura = intervalo_ms
            self.timer.start(intervalo_ms)
            self.logger.info(f"Automatic reading started every {intervalo_ms}ms")
            self.log.emit(f"Lectura automática iniciada cada {intervalo_ms}ms")
        else:
            self.logger.warning("Cannot start automatic reading: not connected to Modbus or timer not initialized")

    def detener_lectura(self) -> None:
        """Stop automatic reading while maintaining connection."""
        if self.timer:
            self.timer.stop()
            self.logger.info("Automatic reading stopped")
            self.log.emit("Lectura automática detenida")

    def read_irradiance(self) -> None:
        """Read solar irradiance from Modbus register with retry logic."""
        self._reader.client = self._client
        self._reader.is_connected = self.is_connected
        self._reader.sqlite_conn = self.sqlite_conn
        self._reader.tabla_sqlite = self.tabla_sqlite
        self._reader.read_irradiance()
        self.is_connected = self._reader.is_connected

    def write_setpoints(self, motor1: float, motor2: float) -> None:
        """Send angle setpoints to ESP8266 via Modbus TCP with retry logic.

        Args:
            motor1: Rotation angle (0-360)
            motor2: Elegation angle (0-145)
        """
        self._writer.client = self._client
        self._writer.is_connected = self.is_connected
        self._writer.safe_state = self.safe_state
        self._writer.write_setpoints(motor1, motor2)
        self.is_connected = self._writer.is_connected
        self.safe_state = self._writer.safe_state

    def configurar_sqlite(self, ruta_db: str, tabla: str) -> bool:
        """Configure SQLite connection for automatic data storage.

        Args:
            ruta_db: Path to database file
            tabla: Table name for storing measurements

        Returns:
            bool: True if configuration successful, False otherwise
        """
        try:
            if self.sqlite_conn:
                self.sqlite_conn.close()

            self.sqlite_conn = sqlite_manager.connect_db(ruta_db)
            self.tabla_sqlite = tabla

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

    def _on_angles_changed(self, rot: float, ele: float, source=None) -> None:
        """Handle angle changes from AngleStateManager.

        Args:
            rot: Rotation angle (0-360)
            ele: Elevation angle (0-145)
            source: Source of angle change (optional)
        """
        rot_int, ele_int = ModbusWriter.validate_angles(rot, ele)

        if self.is_connected and self.angle_manager:
            modo = self.angle_manager.get_mode()
            if modo in ("auto", "manual") and source != "prueba":
                self.logger.debug(f"Angles changed, sending setpoints: rot={rot_int}, ele={ele_int}, mode={modo}")
                self.write_setpoints(rot_int, ele_int)

    def exit_safe_state(self) -> None:
        """Exit safe state manually after resolving the problem."""
        if self.safe_state:
            self.logger.info("Exiting safe state - manual recovery initiated")
            self.log.emit("Saliendo del modo seguro - recuperación manual iniciada")
            self.safe_state = False
        else:
            self.logger.debug("exit_safe_state called but system was not in safe state")

    def is_in_safe_state(self) -> bool:
        """Check if system is in safe state.

        Returns:
            bool: True if system is in safe state, False otherwise
        """
        return self.safe_state


ModbusManager = ModbusClient
