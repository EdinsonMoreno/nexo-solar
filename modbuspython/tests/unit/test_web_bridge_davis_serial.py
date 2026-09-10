"""Tests for Davis serial configuration exposed by WebBridge."""

from __future__ import annotations

from typing import Any

import pytest

pytest.importorskip("PyQt6.QtCore")

from modbuspython.ui.web_bridge import WebBridge


class Signal:
    def connect(self, _slot) -> None:
        pass


class FakeModbus:
    radiacion_actualizada = Signal()
    log = Signal()
    conexion_cambiada = Signal()
    retry_exhausted = Signal()


class FakeDavis:
    weather_data_updated = Signal()
    connection_changed = Signal()
    connection_lost = Signal()
    log = Signal()
    retry_exhausted = Signal()

    def __init__(self) -> None:
        self.values: dict[str, Any] = {
            "transport": "serial",
            "serial_port": "/dev/ttyUSB0",
            "ip_host": "192.168.1.50",
            "ip_port": 22222,
        }
        self.is_connected = False
        self.last_error = ""
        self.read_count = 0
        self.last_reading = None

    def _get_config(self, key: str, default: Any) -> Any:
        return self.values.get(key, default)

    def configure_runtime(self, transport: str, serial_port: str, ip_host: str, ip_port: int) -> None:
        self.values.update(
            {
                "transport": transport,
                "serial_port": serial_port,
                "ip_host": ip_host,
                "ip_port": ip_port,
            }
        )


def test_apply_davis_serial_port_updates_active_config() -> None:
    davis = FakeDavis()
    bridge = WebBridge(FakeModbus(), davis)

    result = bridge.applyDavisSerialPort("COM7")

    assert result["ok"] is True
    assert davis.values["transport"] == "serial"
    assert davis.values["serial_port"] == "COM7"


def test_apply_davis_serial_port_rejects_empty_value() -> None:
    bridge = WebBridge(FakeModbus(), FakeDavis())

    result = bridge.applyDavisSerialPort("  ")

    assert result["ok"] is False
    assert "Seleccion" in result["message"]
