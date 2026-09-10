"""Threaded Davis WeatherLink reader."""

from __future__ import annotations

import time
from typing import Optional

from PyQt6.QtCore import QThread, QTimer, pyqtSignal

from ...config.config_defaults import DEFAULT_CONFIG
from ...exceptions import DavisConnectionError, DavisProtocolError, DavisTransportError
from ..logging_service import LoggingService
from ..repositories.davis_weather_repository import DavisWeatherRepository
from ..retry_strategy import RetryStrategy
from .crc_validator import CRCValidator
from .packet_parser import PacketParser
from .transport import BaseTransport, IPTransport, SerialTransport
from .weather_data import WeatherData


class DavisWeatherLinkReader(QThread):
    """Read Davis LOOP packets without blocking the application interface."""

    weather_data_updated = pyqtSignal(object)
    connection_changed = pyqtSignal(bool)
    connection_lost = pyqtSignal(str)
    log = pyqtSignal(str)
    retry_exhausted = pyqtSignal(str, str)

    WAKE_UP_BYTE = b"\x0a"
    WAKE_UP_RESPONSE = b"\x0a\x0d"
    WAKE_UP_TIMEOUT_S = 1.2
    WAKE_UP_ATTEMPTS = 3
    LOOP_COMMAND = b"LOOP 1\n"
    ACK = b"\x06"
    CRC_RETRY_DELAY_S = 0.5

    def __init__(self, config_manager=None, transport: Optional[BaseTransport] = None, parent=None) -> None:
        super().__init__(parent)
        self.config = config_manager
        self.logger = LoggingService()
        self.crc_validator = CRCValidator()
        self.packet_parser = PacketParser()
        self.transport: Optional[BaseTransport] = transport
        self._runtime_config: dict[str, object] = {}
        self.timer: Optional[QTimer] = None
        self.is_connected = False
        self.is_running = False
        self.last_reading: Optional[WeatherData] = None
        self.last_error = ""
        self.read_count = 0

        self.poll_interval_ms = int(self._get_config("poll_interval_ms", 5000))
        retry_attempts = int(self._get_config("retry_attempts", 3))
        retry_backoff = float(self._get_config("retry_backoff", 1.0))
        self.timeout = float(self._get_config("timeout", 5.0))
        self.retry_strategy = RetryStrategy(
            max_attempts=retry_attempts,
            initial_delay=retry_backoff,
            backoff_factor=2.0,
            max_delay=30.0,
        )
        self.weather_repository = self._build_weather_repository()

    def run(self) -> None:
        """Create the polling timer and start the thread event loop."""
        self.is_running = True
        self.timer = QTimer()
        self.timer.timeout.connect(self.read_once)
        self.logger.info(f"Davis periodic reader initialized every {self.poll_interval_ms}ms")
        self.log.emit(f"Davis: lectura periódica lista cada {self.poll_interval_ms}ms")
        self.connect_station()
        if self.is_connected:
            self.iniciar(self.poll_interval_ms)
        self.exec()
        self.logger.info("Davis reader thread finished")

    def configure_runtime(
        self,
        transport: str,
        serial_port: str,
        ip_host: str,
        ip_port: int,
        poll_interval_ms: Optional[int] = None,
    ) -> None:
        """Update Davis connection settings from the UI without touching config.yaml."""
        self._disconnect_transport()
        self._runtime_config.update(
            {
                "transport": transport,
                "serial_port": serial_port,
                "ip_host": ip_host,
                "ip_port": int(ip_port),
            }
        )
        self._set_config("transport", transport)
        self._set_config("serial_port", serial_port)
        self._set_config("ip_host", ip_host)
        self._set_config("ip_port", int(ip_port))
        if poll_interval_ms is not None:
            self.poll_interval_ms = int(poll_interval_ms)
            self._runtime_config["poll_interval_ms"] = self.poll_interval_ms
            self._set_config("poll_interval_ms", self.poll_interval_ms)

    def connect_station(self) -> bool:
        """Open the configured transport with RetryStrategy."""
        result, success = self._execute_with_retry("Davis Connection", self._connect_once)
        if success:
            self._set_connection(True)
            self.logger.info("Davis weather station connected")
            self.log.emit("Davis: conexión establecida")
            return bool(result)
        self._set_connection(False)
        return False

    def disconnect_station(self) -> None:
        """Disconnect the station and stop periodic polling."""
        self.detener_lectura()
        self._disconnect_transport()
        self._set_connection(False)
        self.logger.info("Davis weather station disconnected")
        self.log.emit("Davis: conexión cerrada")

    def iniciar(self, intervalo_ms: Optional[int] = None) -> None:
        """Start periodic LOOP readings."""
        if intervalo_ms is not None:
            self.poll_interval_ms = int(intervalo_ms)
        if not self.is_connected:
            self.logger.warning("Cannot start Davis periodic reading without an active connection")
            return
        if self.timer is None:
            self.timer = QTimer()
            self.timer.timeout.connect(self.read_once)
        self.timer.start(self.poll_interval_ms)
        self.logger.info(f"Davis periodic reading started every {self.poll_interval_ms}ms")
        self.log.emit(f"Davis: lectura automática iniciada cada {self.poll_interval_ms}ms")

    def detener_lectura(self) -> None:
        """Stop periodic LOOP readings."""
        if self.timer is not None:
            self.timer.stop()
            self.logger.info("Davis periodic reading stopped")
            self.log.emit("Davis: lectura automática detenida")

    def read_once(self) -> Optional[WeatherData]:
        """Read, validate, parse and emit one Davis LOOP packet."""
        data, success = self._execute_with_retry("Davis LOOP Read", self._read_cycle)
        if success and data is not None:
            self.last_reading = data
            self.read_count += 1
            self._save_reading(data)
            self._set_connection(True)
            self.weather_data_updated.emit(data)
            self.logger.debug(
                "Davis LOOP decoded: "
                f"temp_out_c={data.temp_out_c:.2f}, humidity_out={data.humidity_out:.1f}, "
                f"solar_radiation_wm2={data.solar_radiation_wm2:.1f}, wind_dir_deg={data.wind_dir_deg}"
            )
            return data
        self._set_connection(False)
        return None

    def stop(self) -> None:
        """Stop polling, close the transport and finish within 10 seconds."""
        self.is_running = False
        self.detener_lectura()
        self._disconnect_transport()
        self.quit()
        if self.isRunning() and not self.wait(10000):
            self.logger.warning("Davis reader thread did not finish within 10 seconds")
            self.terminate()
            self.wait(1000)

    def _read_cycle(self) -> WeatherData:
        if self.transport is None or not self.transport.is_open():
            self._connect_once()
            self._set_connection(True)
        self._wake_up()
        self._send_loop_command()
        packet = self._read_packet()
        if not self.crc_validator.validate(packet):
            time.sleep(self.CRC_RETRY_DELAY_S)
            raise DavisProtocolError("Davis LOOP packet CRC is invalid")
        data = self.packet_parser.parse(packet)
        self._validate_ranges(data)
        return data

    def _connect_once(self) -> bool:
        self.transport = self.transport or self._build_transport()
        self.transport.connect()
        return self.transport.is_open()

    def _build_transport(self) -> BaseTransport:
        transport_type = str(self._get_config("transport", "serial")).lower()
        if transport_type == "serial":
            baud_rate = int(self._get_config("baud_rate", 19200))
            if baud_rate != 19200:
                self.logger.error("Invalid Davis baud rate configured; expected 19200")
                raise DavisConnectionError("Davis WeatherLink VCP requires baud_rate 19200")
            return SerialTransport(
                port=str(self._get_config("serial_port", "/dev/ttyUSB0")),
                baud_rate=baud_rate,
                timeout=self.timeout,
            )
        if transport_type == "ip":
            return IPTransport(
                host=str(self._get_config("ip_host", "192.168.1.50")),
                port=int(self._get_config("ip_port", 22222)),
                timeout=self.timeout,
            )
        self.logger.error(f"Invalid Davis transport configured: {transport_type}")
        raise DavisConnectionError("Unsupported Davis transport", details={"transport": transport_type})

    def _wake_up(self) -> None:
        if self.transport is None:
            raise DavisTransportError("Davis transport is not initialized")
        for attempt in range(1, self.WAKE_UP_ATTEMPTS + 1):
            self.transport.send(self.WAKE_UP_BYTE)
            response = self.transport.receive(len(self.WAKE_UP_RESPONSE), self.WAKE_UP_TIMEOUT_S)
            if response == self.WAKE_UP_RESPONSE:
                self.logger.debug("Davis wake-up sequence completed")
                return
            self.logger.warning(f"Davis wake-up attempt {attempt} returned {response.hex()}")
        message = "Davis console did not answer the wake-up sequence"
        self.connection_lost.emit(message)
        self.logger.error(message)
        raise DavisTransportError(message)

    def _send_loop_command(self) -> None:
        if self.transport is None:
            raise DavisTransportError("Davis transport is not initialized")
        self.transport.send(self.LOOP_COMMAND)
        ack = self.transport.receive(1, self.timeout)
        if ack != self.ACK:
            self.logger.warning(f"Davis LOOP command was not acknowledged: {ack.hex()}")
            raise DavisProtocolError("Davis LOOP command was not acknowledged", details={"ack": ack.hex()})

    def _read_packet(self) -> bytes:
        if self.transport is None:
            raise DavisTransportError("Davis transport is not initialized")
        packet = self.transport.receive(PacketParser.PACKET_LENGTH, self.timeout)
        if len(packet) != PacketParser.PACKET_LENGTH:
            raise DavisProtocolError(
                "Incomplete Davis LOOP packet",
                details={"expected": PacketParser.PACKET_LENGTH, "actual": len(packet)},
            )
        return packet

    def _validate_ranges(self, data: WeatherData) -> None:
        ranges = {
            "pressure_hpa": (data.pressure_hpa, 800.0, 1100.0),
            "temp_out_c": (data.temp_out_c, -50.0, 60.0),
            "humidity_out": (data.humidity_out, 0.0, 100.0),
            "wind_speed_ms": (data.wind_speed_ms, 0.0, 90.0),
            "wind_dir_deg": (float(data.wind_dir_deg), 0.0, 360.0),
        }
        for field, (value, minimum, maximum) in ranges.items():
            if not minimum <= value <= maximum:
                self.logger.warning(f"Davis WeatherData rejected: {field}={value} outside [{minimum}, {maximum}]")
                raise DavisProtocolError(
                    "Davis WeatherData value outside accepted range",
                    details={"field": field, "value": value, "minimum": minimum, "maximum": maximum},
                )

    def _execute_with_retry(self, operation: str, callback):
        last_error = ""

        def wrapped():
            nonlocal last_error
            try:
                return callback()
            except Exception as exc:
                last_error = str(exc)
                raise

        result, success = self.retry_strategy.execute_with_retry(wrapped)
        if success:
            return result, True

        self.last_error = last_error or "Operation failed after retries"
        self.retry_exhausted.emit(operation, self.last_error)
        self.logger.error(f"Davis retry exhausted for {operation}: {self.last_error}")
        return None, False

    def _disconnect_transport(self) -> None:
        if self.transport is None:
            return
        try:
            self.transport.disconnect()
        except DavisTransportError as exc:
            self.logger.warning(f"Davis transport disconnect failed: {exc}")
        finally:
            self.transport = None

    def _set_connection(self, connected: bool) -> None:
        if self.is_connected != connected:
            self.is_connected = connected
            self.connection_changed.emit(connected)

    def _build_weather_repository(self) -> Optional[DavisWeatherRepository]:
        db_path = self._get_database_path()
        if not db_path:
            return None
        try:
            repository = DavisWeatherRepository(db_path=str(db_path), use_pool=False)
            repository.create_table()
            return repository
        except Exception as exc:
            self.last_error = str(exc)
            self.logger.warning(f"Davis persistence disabled: {exc}")
            return None

    def _save_reading(self, data: WeatherData) -> None:
        if self.weather_repository is None:
            return
        try:
            source = "davis_usb" if str(self._get_config("transport", "serial")).lower() == "serial" else "davis_ip"
            self.weather_repository.insert_reading(data, quality="valid", source=source)
        except Exception as exc:
            self.last_error = str(exc)
            self.logger.warning(f"Davis reading was not saved to SQLite: {exc}")

    def _get_database_path(self) -> Optional[str]:
        if self.config is None:
            return str(DEFAULT_CONFIG["database"].get("path", "data/nexo_solar.db"))
        return self.config.get("database.path", DEFAULT_CONFIG["database"].get("path", "data/nexo_solar.db"))

    def _get_config(self, key: str, default):
        if key in self._runtime_config:
            return self._runtime_config[key]
        if self.config is None:
            return DEFAULT_CONFIG["davis_weatherlink"].get(key, default)
        return self.config.get(f"davis_weatherlink.{key}", DEFAULT_CONFIG["davis_weatherlink"].get(key, default))

    def _set_config(self, key: str, value) -> None:
        if self.config is not None:
            self.config.set(f"davis_weatherlink.{key}", value)
