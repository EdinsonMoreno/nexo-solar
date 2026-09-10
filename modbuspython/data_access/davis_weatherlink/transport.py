"""Transport adapters for Davis WeatherLink communication."""

from __future__ import annotations

import socket
import time
from abc import ABC, abstractmethod
from typing import Optional

from ...exceptions import DavisTransportError

try:  # pragma: no cover - exercised through mocks when pyserial is present
    import serial
except ImportError:  # pragma: no cover - depends on developer environment
    serial = None  # type: ignore[assignment]


class BaseTransport(ABC):
    """Common byte transport contract for Davis serial and TCP links."""

    @abstractmethod
    def connect(self) -> None:
        """Open the underlying transport."""

    @abstractmethod
    def disconnect(self) -> None:
        """Close the underlying transport and release resources."""

    @abstractmethod
    def send(self, data: bytes) -> None:
        """Send all bytes to the station."""

    @abstractmethod
    def receive(self, n_bytes: int, timeout: float) -> bytes:
        """Receive exactly ``n_bytes`` bytes before ``timeout`` expires."""

    @abstractmethod
    def is_open(self) -> bool:
        """Return True when the transport is ready for I/O."""


class SerialTransport(BaseTransport):
    """Davis WeatherLink USB logger transport using serial VCP mode."""

    def __init__(self, port: str, baud_rate: int = 19200, timeout: float = 5.0) -> None:
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self._serial: Optional[object] = None

    def connect(self) -> None:
        if serial is None:
            raise DavisTransportError("pyserial is required for Davis serial transport")

        try:
            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False,
            )
        except Exception as exc:
            raise DavisTransportError(
                "Could not open Davis serial transport",
                details={"port": self.port, "baud_rate": self.baud_rate, "error": str(exc)},
            ) from exc

    def disconnect(self) -> None:
        serial_port = self._serial
        self._serial = None
        if serial_port is not None:
            try:
                serial_port.close()
            except Exception as exc:
                raise DavisTransportError("Could not close Davis serial transport", details={"error": str(exc)}) from exc

    def send(self, data: bytes) -> None:
        if not self.is_open() or self._serial is None:
            raise DavisTransportError("Davis serial transport is not open")

        try:
            written = self._serial.write(data)
            if written != len(data):
                raise DavisTransportError(
                    "Incomplete Davis serial write",
                    details={"expected": len(data), "actual": written},
                )
        except DavisTransportError:
            raise
        except Exception as exc:
            raise DavisTransportError("Davis serial write failed", details={"error": str(exc)}) from exc

    def receive(self, n_bytes: int, timeout: float) -> bytes:
        if not self.is_open() or self._serial is None:
            raise DavisTransportError("Davis serial transport is not open")

        try:
            self._serial.timeout = timeout
            data = self._serial.read(n_bytes)
        except Exception as exc:
            raise DavisTransportError("Davis serial read failed", details={"error": str(exc)}) from exc

        if len(data) != n_bytes:
            raise DavisTransportError(
                "Davis serial read timed out",
                details={"expected": n_bytes, "actual": len(data), "timeout": timeout},
            )
        return data

    def is_open(self) -> bool:
        return bool(self._serial is not None and getattr(self._serial, "is_open", False))


class IPTransport(BaseTransport):
    """Davis WeatherLink TCP transport for IP adapters."""

    def __init__(self, host: str, port: int, timeout: float = 5.0) -> None:
        self.host = host
        self.port = int(port)
        self.timeout = timeout
        self._socket: Optional[socket.socket] = None

    def connect(self) -> None:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.host, self.port))
            self._socket = sock
        except Exception as exc:
            raise DavisTransportError(
                "Could not open Davis IP transport",
                details={"host": self.host, "port": self.port, "error": str(exc)},
            ) from exc

    def disconnect(self) -> None:
        sock = self._socket
        self._socket = None
        if sock is not None:
            try:
                sock.close()
            except Exception as exc:
                raise DavisTransportError("Could not close Davis IP transport", details={"error": str(exc)}) from exc

    def send(self, data: bytes) -> None:
        if not self.is_open() or self._socket is None:
            raise DavisTransportError("Davis IP transport is not open")

        try:
            self._socket.sendall(data)
        except Exception as exc:
            raise DavisTransportError("Davis IP write failed", details={"error": str(exc)}) from exc

    def receive(self, n_bytes: int, timeout: float) -> bytes:
        if not self.is_open() or self._socket is None:
            raise DavisTransportError("Davis IP transport is not open")

        deadline = time.monotonic() + timeout
        chunks: list[bytes] = []
        received = 0
        try:
            self._socket.settimeout(timeout)
            while received < n_bytes:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                self._socket.settimeout(remaining)
                chunk = self._socket.recv(n_bytes - received)
                if not chunk:
                    break
                chunks.append(chunk)
                received += len(chunk)
        except Exception as exc:
            raise DavisTransportError("Davis IP read failed", details={"error": str(exc)}) from exc

        data = b"".join(chunks)
        if len(data) != n_bytes:
            raise DavisTransportError(
                "Davis IP read timed out",
                details={"expected": n_bytes, "actual": len(data), "timeout": timeout},
            )
        return data

    def is_open(self) -> bool:
        return self._socket is not None
