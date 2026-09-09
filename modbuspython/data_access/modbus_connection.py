"""Modbus connection operations with retry logic.

Handles connection establishment to Modbus TCP servers
with automatic retry and exponential backoff.
"""

import traceback

from typing import Optional

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import (
    ModbusException,
    ConnectionException,
)

from modbuspython.exceptions import ModbusConnectionError
from modbuspython.data_access.logging_service import LoggingService


class ModbusConnector:
    """Handles Modbus TCP connection operations.

    Provides connection establishment with retry logic
    and proper exception handling.
    """

    def __init__(
        self,
        ip: str,
        port: int,
        timeout: float,
        retry_strategy,
        logger: LoggingService,
        log_signal,
        connection_signal,
        retry_exhausted_signal,
    ) -> None:
        """Initialize connector.

        Args:
            ip: Modbus server IP address
            port: Modbus server TCP port
            timeout: Connection timeout in seconds
            retry_strategy: RetryStrategy instance
            logger: LoggingService instance
            log_signal: Signal for log messages
            connection_signal: Signal for connection state changes
            retry_exhausted_signal: Signal for retry exhaustion
        """
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.retry_strategy = retry_strategy
        self.logger = logger
        self.log_signal = log_signal
        self.connection_signal = connection_signal
        self.retry_exhausted_signal = retry_exhausted_signal
        self.client: Optional[ModbusTcpClient] = None
        self.is_connected = False
        self.safe_state = False

    def connect(self) -> None:
        """Attempt to connect to Modbus TCP server with retry logic.

        Establishes connection to the Modbus server using the configured IP and port.
        Implements automatic retry with exponential backoff. Emits connection state
        signals and enters safe state if all retries are exhausted.

        Raises:
            ModbusConnectionError: If connection fails after all retry attempts
        """

        def _connect_attempt() -> bool:
            """Internal connection attempt function for retry logic."""
            try:
                self.logger.debug(f"Attempting Modbus connection to {self.ip}:{self.port}")
                self.log_signal.emit(f"[DEBUG] Intentando conectar a {self.ip}:{self.port}")

                self.client = ModbusTcpClient(self.ip, port=self.port, timeout=self.timeout)
                tcp_ok: bool = bool(self.client.connect())  # type: ignore[union-attr]

                if not tcp_ok:
                    raise ModbusConnectionError(
                        "Failed to connect to Modbus device",
                        details={"ip": self.ip, "port": self.port, "timeout": self.timeout},
                    )

                return tcp_ok

            except ConnectionException as e:
                self.logger.error(f"Modbus ConnectionException: {e}")
                self.logger.debug(f"Stack trace: {traceback.format_exc()}")
                raise ModbusConnectionError(
                    f"Modbus connection exception: {str(e)}",
                    details={"ip": self.ip, "port": self.port, "exception_type": type(e).__name__},
                )

            except ModbusException as e:
                self.logger.error(f"Modbus exception during connection: {e}")
                self.logger.debug(f"Stack trace: {traceback.format_exc()}")
                raise ModbusConnectionError(
                    f"Modbus exception: {str(e)}",
                    details={"ip": self.ip, "port": self.port, "exception_type": type(e).__name__},
                )

            except OSError as e:
                self.logger.error(f"Network error during Modbus connection: {e}")
                self.logger.debug(f"Stack trace: {traceback.format_exc()}")
                raise ModbusConnectionError(
                    f"Network error: {str(e)}",
                    details={
                        "ip": self.ip,
                        "port": self.port,
                        "error_code": e.errno if hasattr(e, "errno") else None,
                    },
                )

            except Exception as e:
                self.logger.error(f"Unexpected error during Modbus connection: {e}")
                self.logger.error(f"Stack trace: {traceback.format_exc()}")
                raise ModbusConnectionError(
                    f"Unexpected connection error: {str(e)}",
                    details={"ip": self.ip, "port": self.port, "exception_type": type(e).__name__},
                )

        try:
            result, success = self.retry_strategy.execute_with_retry(_connect_attempt)
            self.is_connected = success

            if self.is_connected:
                self.logger.info(f"Modbus connection established: {self.ip}:{self.port}")
                self.log_signal.emit(f"Conectado a Modbus TCP: {self.ip}:{self.port}")
                self.safe_state = False
            else:
                error_msg = (
                    f"Failed to establish Modbus connection to {self.ip}:{self.port} "
                    f"after {self.retry_strategy.max_attempts} attempts"
                )
                self.logger.error(error_msg)
                self.log_signal.emit(
                    f"No se pudo establecer comunicación Modbus con {self.ip}:{self.port} " f"después de todos los intentos"
                )
                self.safe_state = True
                self.retry_exhausted_signal.emit("Connection", error_msg)

            self.connection_signal.emit(self.is_connected)

        except ModbusConnectionError as e:
            self.logger.error(f"Connection failed after retries: {e}")
            self.is_connected = False
            self.safe_state = True
            self.connection_signal.emit(False)
            self.retry_exhausted_signal.emit("Connection", str(e))

        except Exception as e:
            self.logger.error(f"Unexpected error in conectar: {e}")
            self.logger.error(f"Stack trace: {traceback.format_exc()}")
            self.is_connected = False
            self.safe_state = True
            self.connection_signal.emit(False)

    def disconnect(self) -> None:
        """Disconnect completely from Modbus server.

        Stops the timer, closes the client connection, and emits connection state signal.
        """
        if self.client:
            self.client.close()

        self.is_connected = False
        self.connection_signal.emit(False)
        self.logger.info("Disconnected from Modbus server")
        self.log_signal.emit("Desconectado del servidor Modbus")
