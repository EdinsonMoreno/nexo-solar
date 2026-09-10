"""Unit tests for Davis WeatherLink transports."""

from unittest.mock import Mock, patch

import pytest

from modbuspython.data_access.davis_weatherlink.transport import IPTransport, SerialTransport
from modbuspython.exceptions import DavisTransportError


def test_serial_transport_uses_davis_vcp_parameters() -> None:
    serial_instance = Mock(is_open=True)
    serial_instance.write.return_value = 2
    serial_instance.read.return_value = b"OK"

    with patch("modbuspython.data_access.davis_weatherlink.transport.serial") as serial_module:
        serial_module.EIGHTBITS = 8
        serial_module.PARITY_NONE = "N"
        serial_module.STOPBITS_ONE = 1
        serial_module.Serial.return_value = serial_instance

        transport = SerialTransport("/dev/ttyUSB0", baud_rate=19200, timeout=5.0)
        transport.connect()
        transport.send(b"OK")
        data = transport.receive(2, timeout=1.2)

    serial_module.Serial.assert_called_once_with(
        port="/dev/ttyUSB0",
        baudrate=19200,
        bytesize=8,
        parity="N",
        stopbits=1,
        timeout=5.0,
        xonxoff=False,
        rtscts=False,
        dsrdtr=False,
    )
    assert data == b"OK"


def test_serial_transport_raises_when_pyserial_is_missing() -> None:
    with patch("modbuspython.data_access.davis_weatherlink.transport.serial", None):
        with pytest.raises(DavisTransportError, match="pyserial"):
            SerialTransport("/dev/ttyUSB0").connect()


def test_ip_transport_sends_and_receives_exact_bytes() -> None:
    socket_instance = Mock()
    socket_instance.recv.side_effect = [b"A", b"CK"]

    with patch("modbuspython.data_access.davis_weatherlink.transport.socket.socket") as socket_factory:
        socket_factory.return_value = socket_instance
        transport = IPTransport("192.168.1.50", 22222, timeout=5.0)
        transport.connect()
        transport.send(b"LOOP 1\r")
        data = transport.receive(3, timeout=1.0)

    socket_instance.connect.assert_called_once_with(("192.168.1.50", 22222))
    socket_instance.sendall.assert_called_once_with(b"LOOP 1\r")
    assert data == b"ACK"


def test_ip_transport_raises_on_short_read() -> None:
    socket_instance = Mock()
    socket_instance.recv.side_effect = [b"A", b""]

    with patch("modbuspython.data_access.davis_weatherlink.transport.socket.socket") as socket_factory:
        socket_factory.return_value = socket_instance
        transport = IPTransport("192.168.1.50", 22222, timeout=5.0)
        transport.connect()
        with pytest.raises(DavisTransportError, match="timed out"):
            transport.receive(3, timeout=1.0)
