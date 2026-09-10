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


def test_crc_matches_davis_reference_example() -> None:
    """Davis reference example C6 CE A2 03 produces CRC E2 B4."""
    payload = bytes.fromhex("C6 CE A2 03")

    assert CRCValidator().calculate_crc(payload) == 0xE2B4
