"""Parser for Davis WeatherLink LOOP packets."""

import json
import struct
from typing import Any

from ...exceptions import DavisProtocolError
from .unit_conversion import fahrenheit_to_celsius, inches_to_mm, inhg_to_hpa, mph_to_ms
from .weather_data import WeatherData


class PacketParser:
    """Decode Davis LOOP packet bytes into :class:`WeatherData`."""

    PACKET_LENGTH = 99
    SIGNATURE = b"LOO"
    SIGNATURE_OFFSET = 0

    def __init__(self, rain_click_inches: float = 0.01) -> None:
        self.rain_click_inches = rain_click_inches

    def parse(self, packet: bytes) -> WeatherData:
        """Parse a LOOP packet using the local Davis feature specification."""
        self._validate_packet(packet)

        pressure_inhg = self._uint16_le(packet, 7) / 1000.0
        temp_in_f = self._int16_le(packet, 9) / 10.0
        temp_out_f = self._int16_le(packet, 12) / 10.0
        wind_speed_mph = packet[14]
        wind_speed_avg_mph = packet[15]
        rain_rate_inches = self._uint16_le(packet, 41) * self.rain_click_inches

        return WeatherData(
            temp_out_c=fahrenheit_to_celsius(temp_out_f),
            temp_in_c=fahrenheit_to_celsius(temp_in_f),
            humidity_out=float(packet[33]),
            humidity_in=float(packet[11]),
            pressure_hpa=inhg_to_hpa(pressure_inhg),
            wind_speed_ms=mph_to_ms(wind_speed_mph),
            wind_speed_avg_ms=mph_to_ms(wind_speed_avg_mph),
            wind_dir_deg=self._uint16_le(packet, 16),
            rain_rate_mm=inches_to_mm(rain_rate_inches),
            rain_storm_mm=inches_to_mm(self._uint16_le(packet, 46) / 100.0),
            rain_day_mm=inches_to_mm(self._uint16_le(packet, 50) / 100.0),
            rain_month_mm=inches_to_mm(self._uint16_le(packet, 52) / 100.0),
            rain_year_mm=inches_to_mm(self._uint16_le(packet, 54) / 100.0),
            solar_radiation_wm2=float(self._uint16_le(packet, 44)),
            uv_index=packet[43] / 10.0,
        )

    def format_weather_data(self, data: WeatherData) -> str:
        """Format WeatherData as structured text with explicit units."""
        payload: dict[str, dict[str, Any]] = {
            "temp_out_c": {"value": data.temp_out_c, "unit": "C"},
            "temp_in_c": {"value": data.temp_in_c, "unit": "C"},
            "humidity_out": {"value": data.humidity_out, "unit": "% RH"},
            "humidity_in": {"value": data.humidity_in, "unit": "% RH"},
            "pressure_hpa": {"value": data.pressure_hpa, "unit": "hPa"},
            "wind_speed_ms": {"value": data.wind_speed_ms, "unit": "m/s"},
            "wind_speed_avg_ms": {"value": data.wind_speed_avg_ms, "unit": "m/s"},
            "wind_dir_deg": {"value": data.wind_dir_deg, "unit": "deg"},
            "rain_rate_mm": {"value": data.rain_rate_mm, "unit": "mm"},
            "rain_storm_mm": {"value": data.rain_storm_mm, "unit": "mm"},
            "rain_day_mm": {"value": data.rain_day_mm, "unit": "mm"},
            "rain_month_mm": {"value": data.rain_month_mm, "unit": "mm"},
            "rain_year_mm": {"value": data.rain_year_mm, "unit": "mm"},
            "solar_radiation_wm2": {"value": data.solar_radiation_wm2, "unit": "W/m2"},
            "uv_index": {"value": data.uv_index, "unit": "index"},
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    def parse_weather_data(self, text: str) -> WeatherData:
        """Parse the structured representation created by format_weather_data."""
        payload = json.loads(text)
        values = {key: item["value"] for key, item in payload.items()}
        values["wind_dir_deg"] = int(values["wind_dir_deg"])
        return WeatherData(**values)

    def _validate_packet(self, packet: bytes) -> None:
        if len(packet) != self.PACKET_LENGTH:
            raise DavisProtocolError(
                "Invalid Davis LOOP packet length",
                details={"expected": self.PACKET_LENGTH, "actual": len(packet)},
            )
        signature_end = self.SIGNATURE_OFFSET + len(self.SIGNATURE)
        actual_signature = packet[self.SIGNATURE_OFFSET : signature_end]
        if actual_signature != self.SIGNATURE:
            raise DavisProtocolError(
                "Invalid Davis LOOP packet signature",
                details={"expected": self.SIGNATURE.decode("ascii"), "actual": actual_signature.hex()},
            )

    @staticmethod
    def _uint16_le(packet: bytes, offset: int) -> int:
        return struct.unpack_from("<H", packet, offset)[0]

    @staticmethod
    def _int16_le(packet: bytes, offset: int) -> int:
        return struct.unpack_from("<h", packet, offset)[0]
