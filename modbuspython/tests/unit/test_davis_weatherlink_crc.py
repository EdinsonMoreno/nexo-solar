"""Unit tests for Davis WeatherLink CRC validation."""

from modbuspython.data_access.davis_weatherlink import CRCValidator


def make_packet(payload: bytes) -> bytes:
    validator = CRCValidator()
    crc = validator.calculate_crc(payload)
    return payload + crc.to_bytes(2, byteorder="big")


def test_crc_validator_accepts_packet_with_matching_crc() -> None:
    payload = bytes(range(97))
    packet = make_packet(payload)

    assert CRCValidator().validate(packet)


def test_crc_validator_rejects_packet_with_changed_payload() -> None:
    packet = bytearray(make_packet(bytes(range(97))))
    packet[10] ^= 0xFF

    assert not CRCValidator().validate(bytes(packet))


def test_crc_validator_rejects_invalid_packet_length() -> None:
    assert not CRCValidator().validate(b"short")
