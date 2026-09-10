"""Unit tests for Davis serial port discovery."""

from __future__ import annotations

from types import SimpleNamespace

from modbuspython.data_access.davis_weatherlink import serial_ports


def make_port(device: str, description: str = "", hwid: str = "", manufacturer: str = "") -> SimpleNamespace:
    return SimpleNamespace(device=device, description=description, hwid=hwid, manufacturer=manufacturer)


def test_list_serial_ports_detects_linux_candidates(monkeypatch) -> None:
    ports = [
        make_port("/dev/ttyS0", "UART", "PNP0501", ""),
        make_port("/dev/ttyUSB0", "USB Serial Port", "USB VID:PID=10C4:EA60", "Silicon Labs"),
        make_port("/dev/ttyACM1", "CDC ACM", "USB VID:PID=1234:5678", ""),
    ]
    monkeypatch.setattr(serial_ports, "list_ports", SimpleNamespace(comports=lambda: ports))

    result = serial_ports.list_serial_ports()

    assert [port["device"] for port in result][:2] == ["/dev/ttyUSB0", "/dev/ttyACM1"]
    assert result[0]["is_likely_davis"] is True
    assert result[0]["manufacturer"] == "Silicon Labs"


def test_list_serial_ports_keeps_windows_com_names(monkeypatch) -> None:
    ports = [
        make_port("COM9", "USB Serial Device", "USB VID:PID=10C4:EA60", "Silicon Labs"),
        make_port("COM3", "Bluetooth Serial", "BTHENUM", "Microsoft"),
    ]
    monkeypatch.setattr(serial_ports, "list_ports", SimpleNamespace(comports=lambda: ports))

    result = serial_ports.list_serial_ports()

    assert result[0]["device"] == "COM9"
    assert result[0]["is_likely_davis"] is True
    assert result[1]["device"] == "COM3"


def test_likely_davis_uses_metadata_hints() -> None:
    assert serial_ports.is_likely_davis_port("COM4", "Davis WeatherLink USB", "", "")
    assert serial_ports.is_likely_davis_port("COM5", "USB Serial", "", "FTDI")
    assert not serial_ports.is_likely_davis_port("COM6", "Bluetooth", "", "Microsoft")
