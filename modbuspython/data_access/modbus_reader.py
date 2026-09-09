"""Modbus read operations with retry logic.

Handles reading of irradiance values from Modbus registers
with automatic retry and exponential backoff.
"""

import sqlite3
import traceback
from datetime import datetime
from typing import Optional

from pymodbus.exceptions import (
    ModbusIOException,
    ConnectionException,
    ModbusException,
)

from modbuspython.exceptions import ModbusConnectionError, ModbusOperationError
from modbuspython.data_access.logging_service import LoggingService


class ModbusReader:
    """Handles Modbus read operations.

    Provides irradiance reading with retry logic,
    value conversion, and optional SQLite storage.
    """

    def __init__(
        self,
        client,
        ip: str,
        port: int,
        register_address: int,
        retry_strategy,
        logger: LoggingService,
        log_signal,
        radiation_signal,
        connection_signal,
        retry_exhausted_signal,
    ) -> None:
        """Initialize reader.

        Args:
            client: Modbus TCP client instance
            ip: Modbus server IP address
            port: Modbus server TCP port
            register_address: Register address for irradiance
            retry_strategy: RetryStrategy instance
            logger: LoggingService instance
            log_signal: Signal for log messages
            radiation_signal: Signal for radiation updates
            connection_signal: Signal for connection state changes
            retry_exhausted_signal: Signal for retry exhaustion
        """
        self.client = client
        self.ip = ip
        self.port = port
        self.register_address = register_address
        self.retry_strategy = retry_strategy
        self.logger = logger
        self.log_signal = log_signal
        self.radiation_signal = radiation_signal
        self.connection_signal = connection_signal
        self.retry_exhausted_signal = retry_exhausted_signal
        self.is_connected = True
        self.sqlite_conn: Optional[sqlite3.Connection] = None
        self.tabla_sqlite: Optional[str] = None

    def read_irradiance(self) -> None:
        """Read solar irradiance from Modbus register with retry logic.

        Executes periodically according to configured interval. Reads the irradiance
        value from the configured Modbus register, validates it, and emits the result.
        Implements automatic retry with exponential backoff on failures.
        """
        if not self.is_connected:
            self.logger.warning("Cannot read radiation: not connected to Modbus")
            self.log_signal.emit("No conectado a Modbus para leer radiación")
            return

        def _read_attempt():
            """Internal read attempt function for retry logic."""
            try:
                self.logger.debug(f"Reading input register {self.register_address} from {self.ip}:{self.port}")
                self.log_signal.emit(f"[DEBUG] Leyendo input register {self.register_address} en {self.ip}:{self.port}")

                rr = self.client.read_input_registers(address=self.register_address, count=1)

                self.logger.debug(f"Modbus read response: {rr}")
                self.log_signal.emit(f"[DEBUG] Respuesta lectura: {rr}")

                if rr is None:
                    raise ModbusOperationError(
                        "Read operation returned None",
                        details={"register": self.register_address, "operation": "read_input_registers"},
                    )

                if hasattr(rr, "isError") and rr.isError():
                    raise ModbusOperationError(
                        "Modbus device returned error response",
                        details={"register": self.register_address, "response": str(rr)},
                    )

                if not hasattr(rr, "registers") or not rr.registers:
                    raise ModbusOperationError(
                        "No registers in response",
                        details={"register": self.register_address, "response": str(rr)},
                    )

                return rr

            except ModbusIOException as e:
                self.logger.error(f"Modbus I/O exception during read: {e}")
                self.logger.debug(f"Stack trace: {traceback.format_exc()}")
                raise ModbusOperationError(
                    f"Modbus I/O error: {str(e)}",
                    details={"register": self.register_address, "exception_type": type(e).__name__},
                )

            except ConnectionException as e:
                self.logger.error(f"Connection lost during read operation: {e}")
                self.logger.debug(f"Stack trace: {traceback.format_exc()}")
                raise ModbusConnectionError(
                    f"Connection lost: {str(e)}",
                    details={"register": self.register_address, "exception_type": type(e).__name__},
                )

            except ModbusException as e:
                self.logger.error(f"Modbus exception during read: {e}")
                self.logger.debug(f"Stack trace: {traceback.format_exc()}")
                raise ModbusOperationError(
                    f"Modbus exception: {str(e)}",
                    details={"register": self.register_address, "exception_type": type(e).__name__},
                )

            except Exception as e:
                self.logger.error(f"Unexpected error during read operation: {e}")
                self.logger.error(f"Stack trace: {traceback.format_exc()}")
                raise ModbusOperationError(
                    f"Unexpected read error: {str(e)}",
                    details={"register": self.register_address, "exception_type": type(e).__name__},
                )

        try:
            rr, success = self.retry_strategy.execute_with_retry(_read_attempt)

            if success and rr is not None:
                valor_raw = rr.registers[0]
                valor_convertido = valor_raw / 100.0

                self._guardar_en_sqlite(valor_convertido)

                self.radiation_signal.emit(valor_convertido)
                self.logger.debug(f"Solar radiation read: {valor_convertido:.2f} W/m² (raw: {valor_raw})")
                self.log_signal.emit(f"Radiación solar: {valor_convertido:.2f} W/m² (raw: {valor_raw})")

            else:
                error_msg = (
                    f"Failed to read radiation from {self.ip}:{self.port} "
                    f"after {self.retry_strategy.max_attempts} attempts"
                )
                self.logger.error(error_msg)
                self.log_signal.emit("No se pudo leer radiación después de todos los intentos")
                self.retry_exhausted_signal.emit("Read Radiation", error_msg)
                self.is_connected = False
                self.connection_signal.emit(False)

        except (ModbusOperationError, ModbusConnectionError) as e:
            self.logger.error(f"Read operation failed after retries: {e}")
            self.is_connected = False
            self.connection_signal.emit(False)
            self.retry_exhausted_signal.emit("Read Radiation", str(e))

        except Exception as e:
            self.logger.error(f"Unexpected error in leer_radiacion: {e}")
            self.logger.error(f"Stack trace: {traceback.format_exc()}")
            self.log_signal.emit(f"Error inesperado al leer radiación: {e}")

    def _guardar_en_sqlite(self, irradiancia: float) -> None:
        """Save irradiance measurement to SQLite if configured.

        Args:
            irradiancia: Irradiance value in W/m²
        """
        if self.sqlite_conn is None or self.tabla_sqlite is None:
            return

        try:
            ahora = datetime.now()
            fecha = ahora.strftime("%Y-%m-%d")
            hora = ahora.strftime("%H:%M:%S")

            from modbuspython.backend import sqlite_manager

            sqlite_manager.insert_record(self.sqlite_conn, self.tabla_sqlite, fecha, hora, irradiancia)
            self.logger.debug(f"Radiation data saved to SQLite: {irradiancia:.2f} W/m²")

        except Exception as e:
            self.logger.error(f"Error saving to SQLite: {e}")
            self.log_signal.emit(f"Error guardando en SQLite: {e}")
