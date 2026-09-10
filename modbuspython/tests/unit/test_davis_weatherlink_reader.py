"""Unit tests for DavisWeatherLinkReader."""

from __future__ import annotations

from typing import Any

import pytest

pytest.importorskip("PyQt6.QtCore")

from modbuspython.data_access.davis_weatherlink import DavisWeatherLinkReader
from modbuspython.data_access.davis_weatherlink.crc_validator import CRCValidator
from modbuspython.data_access.retry_strategy import RetryStrategy
from modbuspython.exceptions import DavisConnectionError, DavisTransportError


class FakeConfig:
    def __init__(self, values: dict[str, Any] | None = None) -> None:
        self.values = values or {}

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.values[key] = value


class FakeTransport:
    def __init__(self, responses: list[bytes]) -> None:
        self.responses = list(responses)
        self.sent: list[bytes] = []
        self.open = False
        self.disconnect_called = False

    def connect(self) -> None:
        self.open = True

    def disconnect(self) -> None:
        self.disconnect_called = True
        self.open = False

    def send(self, data: bytes) -> None:
        if not self.open:
            raise DavisTransportError("closed")
        self.sent.append(data)

    def receive(self, n_bytes: int, timeout: float) -> bytes:
        if not self.responses:
            raise DavisTransportError("no response")
        return self.responses.pop(0)

    def is_open(self) -> bool:
        return self.open


def put_uint16_le(packet: bytearray, offset: int, value: int) -> None:
    packet[offset : offset + 2] = value.to_bytes(2, byteorder="little", signed=False)


def put_int16_le(packet: bytearray, offset: int, value: int) -> None:
    packet[offset : offset + 2] = value.to_bytes(2, byteorder="little", signed=True)


def make_loop_packet(outside_temp_tenths_f: int = 863, humidity_out: int = 68) -> bytes:
    packet = bytearray(99)
    packet[0:3] = b"LOO"
    put_uint16_le(packet, 7, 29921)
    put_int16_le(packet, 9, 754)
    packet[11] = 45
    put_int16_le(packet, 12, outside_temp_tenths_f)
    packet[14] = 8
    packet[15] = 6
    put_uint16_le(packet, 16, 270)
    packet[33] = humidity_out
    put_uint16_le(packet, 41, 3)
    packet[43] = 72
    put_uint16_le(packet, 44, 925)
    put_uint16_le(packet, 46, 12)
    put_uint16_le(packet, 50, 25)
    put_uint16_le(packet, 52, 140)
    put_uint16_le(packet, 54, 1200)
    crc = CRCValidator().calculate_crc(bytes(packet[:97]))
    packet[97:99] = crc.to_bytes(2, byteorder="big")
    return bytes(packet)


def make_reader(transport: FakeTransport) -> DavisWeatherLinkReader:
    reader = DavisWeatherLinkReader(config_manager=FakeConfig(), transport=transport)
    reader.retry_strategy = RetryStrategy(max_attempts=1, initial_delay=0.0, backoff_factor=1.0)
    return reader


def test_reader_performs_wake_up_loop_read_and_emits_weather_data() -> None:
    transport = FakeTransport([b"\n\r", b"\x06", make_loop_packet()])
    reader = make_reader(transport)
    readings = []
    connection_states = []
    reader.weather_data_updated.connect(readings.append)
    reader.connection_changed.connect(connection_states.append)

    data = reader.read_once()

    assert data is not None
    assert transport.sent == [b"\x0a", b"LOOP 1\n"]
    assert readings == [data]
    assert connection_states == [True]
    assert data.solar_radiation_wm2 == 925


def test_reader_rejects_out_of_range_weather_data_without_emit() -> None:
    packet = make_loop_packet(outside_temp_tenths_f=2000)
    reader = make_reader(FakeTransport([b"\n\r", b"\x06", packet]))
    readings = []
    retries = []
    reader.weather_data_updated.connect(readings.append)
    reader.retry_exhausted.connect(lambda operation, error: retries.append((operation, error)))

    data = reader.read_once()

    assert data is None
    assert readings == []
    assert retries
    assert retries[0][0] == "Davis LOOP Read"


def test_reader_builds_ip_transport_from_configuration() -> None:
    config = FakeConfig(
        {
            "davis_weatherlink.transport": "ip",
            "davis_weatherlink.ip_host": "10.0.0.20",
            "davis_weatherlink.ip_port": 22222,
        }
    )
    reader = DavisWeatherLinkReader(config_manager=config)

    transport = reader._build_transport()

    assert transport.host == "10.0.0.20"
    assert transport.port == 22222


def test_reader_rejects_invalid_transport_configuration() -> None:
    config = FakeConfig({"davis_weatherlink.transport": "bluetooth"})
    reader = DavisWeatherLinkReader(config_manager=config)

    with pytest.raises(DavisConnectionError):
        reader._build_transport()


def test_reader_stop_closes_transport_even_when_not_running() -> None:
    transport = FakeTransport([])
    transport.open = True
    reader = make_reader(transport)

    reader.stop()

    assert transport.disconnect_called
