"""Serial port discovery for Davis WeatherLink USB loggers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:  # pragma: no cover - ImportError path depends on the runtime image.
    from serial.tools import list_ports
except ImportError:  # pragma: no cover
    list_ports = None  # type: ignore[assignment]


DAVIS_HINTS = (
    "davis",
    "weatherlink",
    "silicon labs",
    "silabs",
    "cp210",
    "cp210x",
    "ftdi",
    "usb serial",
    "usb-serial",
)

LINUX_SERIAL_PREFIXES = ("/dev/ttyusb", "/dev/ttyacm")


@dataclass(frozen=True)
class SerialPortInfo:
    """Normalized serial port metadata exposed to the web UI."""

    device: str
    description: str
    hwid: str
    manufacturer: str
    is_likely_davis: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "device": self.device,
            "description": self.description,
            "hwid": self.hwid,
            "manufacturer": self.manufacturer,
            "is_likely_davis": self.is_likely_davis,
        }


def list_serial_ports() -> list[dict[str, Any]]:
    """Return serial ports visible to pyserial without shelling out."""

    if list_ports is None:
        return []
    ports = [_normalize_port(port) for port in list_ports.comports()]
    ports.sort(
        key=lambda port: (
            -_davis_score(port.device, port.description, port.hwid, port.manufacturer),
            _natural_device_key(port.device),
        )
    )
    return [port.as_dict() for port in ports]


def _normalize_port(port: Any) -> SerialPortInfo:
    device = str(getattr(port, "device", "") or "")
    description = str(getattr(port, "description", "") or "")
    hwid = str(getattr(port, "hwid", "") or "")
    manufacturer = str(getattr(port, "manufacturer", "") or "")
    return SerialPortInfo(
        device=device,
        description=description,
        hwid=hwid,
        manufacturer=manufacturer,
        is_likely_davis=is_likely_davis_port(device, description, hwid, manufacturer),
    )


def is_likely_davis_port(device: str, description: str = "", hwid: str = "", manufacturer: str = "") -> bool:
    """Detect likely Davis USB/VCP adapters from stable pyserial metadata."""

    return _davis_score(device, description, hwid, manufacturer) > 0


def _davis_score(device: str, description: str = "", hwid: str = "", manufacturer: str = "") -> int:
    haystack = " ".join((device, description, hwid, manufacturer)).lower()
    if any(hint in haystack for hint in DAVIS_HINTS):
        return 2
    if device.lower().startswith(LINUX_SERIAL_PREFIXES):
        return 1
    return 0


def _natural_device_key(device: str) -> tuple[str, int, str]:
    prefix = device.rstrip("0123456789")
    suffix = device[len(prefix) :]
    return (prefix.lower(), int(suffix or "0"), device.lower())
