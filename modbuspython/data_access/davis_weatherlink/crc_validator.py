"""CRC-CCITT validation for Davis LOOP packets."""

from ..logging_service import LoggingService


class CRCValidator:
    """Calculate and validate the CRC used by Davis LOOP packets."""

    PACKET_LENGTH = 99
    PAYLOAD_LENGTH = 97
    POLYNOMIAL = 0x1021

    def __init__(self) -> None:
        self._logger = LoggingService()
        self._crc_table = self._build_table()

    def _build_table(self) -> list[int]:
        """Build the 256-entry lookup table for CRC-CCITT."""
        table = []
        for byte in range(256):
            crc = byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = ((crc << 1) ^ self.POLYNOMIAL) & 0xFFFF
                else:
                    crc = (crc << 1) & 0xFFFF
            table.append(crc)
        return table

    def calculate_crc(self, data: bytes) -> int:
        """Return the CRC-CCITT accumulator for the supplied bytes."""
        crc = 0
        for byte in data:
            crc = self._crc_table[((crc >> 8) ^ byte) & 0xFF] ^ ((crc << 8) & 0xFFFF)
        return crc & 0xFFFF

    def validate(self, packet: bytes) -> bool:
        """Return True when a 99-byte LOOP packet carries a valid CRC."""
        if len(packet) != self.PACKET_LENGTH:
            self._logger.warning(f"Davis LOOP packet length invalid: {len(packet)} bytes")
            return False

        calculated_crc = self.calculate_crc(packet[: self.PAYLOAD_LENGTH])
        expected_crc = int.from_bytes(packet[self.PAYLOAD_LENGTH : self.PACKET_LENGTH], byteorder="big")
        is_valid = calculated_crc == expected_crc
        if not is_valid:
            self._logger.warning(
                "Davis LOOP CRC invalid: "
                f"expected=0x{expected_crc:04X}, calculated=0x{calculated_crc:04X}"
            )
        return is_valid
