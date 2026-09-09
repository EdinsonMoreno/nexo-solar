"""Modbus write operations with retry logic.

Handles writing of angle setpoints to Modbus registers
with automatic retry, validation, and safe state management.
"""

import traceback
from typing import Tuple

from pymodbus.exceptions import (
    ModbusIOException,
    ConnectionException,
    ParameterException,
    ModbusException,
)

from modbuspython.exceptions import ModbusConnectionError, ModbusOperationError
from modbuspython.data_access.logging_service import LoggingService


class ModbusWriter:
    """Handles Modbus write operations.

    Provides angle setpoint writing with retry logic,
    value validation, and safe state management.
    """

    def __init__(
        self,
        client,
        ip: str,
        port: int,
        reg_motor1: int,
        reg_motor2: int,
        retry_strategy,
        logger: LoggingService,
        log_signal,
        connection_signal,
        retry_exhausted_signal,
    ) -> None:
        """Initialize writer.

        Args:
            client: Modbus TCP client instance
            ip: Modbus server IP address
            port: Modbus server TCP port
            reg_motor1: Register address for rotation (motor 1)
            reg_motor2: Register address for elevation (motor 2)
            retry_strategy: RetryStrategy instance
            logger: LoggingService instance
            log_signal: Signal for log messages
            connection_signal: Signal for connection state changes
            retry_exhausted_signal: Signal for retry exhaustion
        """
        self.client = client
        self.ip = ip
        self.port = port
        self.reg_motor1 = reg_motor1
        self.reg_motor2 = reg_motor2
        self.retry_strategy = retry_strategy
        self.logger = logger
        self.log_signal = log_signal
        self.connection_signal = connection_signal
        self.retry_exhausted_signal = retry_exhausted_signal
        self.is_connected = True
        self.safe_state = False

    @staticmethod
    def validate_angles(rot: float, ele: float) -> Tuple[int, int]:
        """Validate and normalize angle values before sending via Modbus.

        Converts angles to integers, rounds them, and clamps them to valid ranges.

        Args:
            rot: Rotation angle (0-360)
            ele: Elevation angle (0-145)

        Returns:
            Tuple[int, int]: Validated (rotation, elevation) angles
        """
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

    def write_setpoints(self, motor1: float, motor2: float) -> None:
        """Send angle setpoints to ESP8266 via Modbus TCP with retry logic.

        Writes rotation and elevation angles to Modbus registers. System enters
        safe state if write operation fails after all retry attempts.

        Args:
            motor1: Rotation angle (0-360)
            motor2: Elevation angle (0-145)
        """
        if self.safe_state:
            self.logger.warning("Cannot write setpoints: system is in safe state after critical error")
            self.log_signal.emit("No se pueden escribir consignas: sistema en modo seguro después de error crítico")
            return

        if not self.is_connected:
            self.logger.warning("Cannot write setpoints: not connected to Modbus")
            self.log_signal.emit("No conectado a Modbus para escribir consignas")
            return

        rot_int, ele_int = self.validate_angles(motor1, motor2)
        self.logger.debug(f"Preparing to write setpoints: Rotation={rot_int}, Elevation={ele_int}")
        self.log_signal.emit(f"[DEBUG] Preparando envío de consignas: Rotación={rot_int}, Elevación={ele_int}")

        def _write_attempt():
            """Internal write attempt function for retry logic."""
            try:
                res1 = self.client.write_register(address=self.reg_motor1, value=rot_int)
                res2 = self.client.write_register(address=self.reg_motor2, value=ele_int)

                if res1 is None or (hasattr(res1, "isError") and res1.isError()):
                    raise ModbusOperationError(
                        "Failed to write Motor1 register",
                        details={"register": self.reg_motor1, "value": rot_int, "response": str(res1)},
                    )

                if res2 is None or (hasattr(res2, "isError") and res2.isError()):
                    raise ModbusOperationError(
                        "Failed to write Motor2 register",
                        details={"register": self.reg_motor2, "value": ele_int, "response": str(res2)},
                    )

                return (res1, res2)

            except ModbusIOException as e:
                self.logger.error(f"Modbus I/O exception during write: {e}")
                self.logger.debug(f"Stack trace: {traceback.format_exc()}")
                raise ModbusOperationError(
                    f"Modbus I/O error: {str(e)}",
                    details={"motor1": rot_int, "motor2": ele_int, "exception_type": type(e).__name__},
                )

            except ConnectionException as e:
                self.logger.error(f"Connection lost during write operation: {e}")
                self.logger.debug(f"Stack trace: {traceback.format_exc()}")
                raise ModbusConnectionError(
                    f"Connection lost: {str(e)}",
                    details={"motor1": rot_int, "motor2": ele_int, "exception_type": type(e).__name__},
                )

            except ParameterException as e:
                self.logger.error(f"Invalid parameters for write operation: {e}")
                self.logger.debug(f"Stack trace: {traceback.format_exc()}")
                raise ModbusOperationError(
                    f"Invalid parameters: {str(e)}",
                    details={"motor1": rot_int, "motor2": ele_int, "exception_type": type(e).__name__},
                )

            except ModbusException as e:
                self.logger.error(f"Modbus exception during write: {e}")
                self.logger.debug(f"Stack trace: {traceback.format_exc()}")
                raise ModbusOperationError(
                    f"Modbus exception: {str(e)}",
                    details={"motor1": rot_int, "motor2": ele_int, "exception_type": type(e).__name__},
                )

            except Exception as e:
                self.logger.error(f"Unexpected error during write operation: {e}")
                self.logger.error(f"Stack trace: {traceback.format_exc()}")
                raise ModbusOperationError(
                    f"Unexpected write error: {str(e)}",
                    details={"motor1": rot_int, "motor2": ele_int, "exception_type": type(e).__name__},
                )

        try:
            result, success = self.retry_strategy.execute_with_retry(_write_attempt)

            if success:
                self.logger.debug(f"Setpoints written successfully: Motor1={rot_int}, Motor2={ele_int}")
                self.log_signal.emit(f"Consignas enviadas correctamente: Motor1={rot_int}, Motor2={ele_int}")

            else:
                error_msg = (
                    f"Failed to write setpoints to {self.ip}:{self.port} after "
                    f"{self.retry_strategy.max_attempts} attempts "
                    f"(Motor1={rot_int}, Motor2={ele_int})"
                )
                self.logger.error(error_msg)
                self.log_signal.emit(
                    f"Error al escribir consignas después de todos los intentos: " f"Motor1={rot_int}, Motor2={ele_int}"
                )
                self.safe_state = True
                self.retry_exhausted_signal.emit("Write Setpoints", error_msg)

        except ModbusOperationError as e:
            self.logger.error(f"Write operation failed after retries: {e}")
            self.safe_state = True
            self.retry_exhausted_signal.emit("Write Setpoints", str(e))

        except ModbusConnectionError as e:
            self.logger.error(f"Connection lost during write operation: {e}")
            self.is_connected = False
            self.safe_state = True
            self.connection_signal.emit(False)
            self.retry_exhausted_signal.emit("Write Setpoints", str(e))

        except Exception as e:
            self.logger.error(f"Unexpected error in escribir_consignas: {e}")
            self.logger.error(f"Stack trace: {traceback.format_exc()}")
            self.safe_state = True
            self.log_signal.emit(f"Error inesperado al escribir consignas: {e}")
