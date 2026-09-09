"""Unit tests for Davis WeatherLink LOOP packet parsing."""

import pytest

from modbuspython.exceptions import DavisProtocolError
from modbuspython.data_access.davis_weatherlink import PacketParser, WeatherData
from modbuspython.data_access.davis_weatherlink.crc_validator import CRCValidator


def put_uint16_le(packet: bytearray, offset: int, value: int) -> None:
    packet[offset : offset + 2] = value.to_bytes(2, byteorder="little", signed=False)


def put_int16_le(packet: bytearray, offset: int, value: int) -> None:
    packet[offset : offset + 2] = value.to_bytes(2, byteorder="little", signed=True)


def make_loop_packet() -> bytes:
    packet = bytearray(99)
    packet[1:4] = b"LOO"
    put_uint16_le(packet, 7, 29921)
    put_int16_le(packet, 9, 754)
    packet[11] = 45
    put_int16_le(packet, 12, 863)
    packet[14] = 8
    packet[15] = 6
    put_uint16_le(packet, 16, 270)
    packet[33] = 68
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


def test_packet_parser_decodes_loop_packet_to_si_units() -> None:
    data = PacketParser().parse(make_loop_packet())

    assert data.pressure_hpa == pytest.approx(29.921 * 33.8639)
    assert data.temp_in_c == pytest.approx(24.111, abs=0.001)
    assert data.temp_out_c == pytest.approx(30.166, abs=0.001)
    assert data.humidity_in == 45
    assert data.humidity_out == 68
    assert data.wind_speed_ms == pytest.approx(3.57632)
    assert data.wind_speed_avg_ms == pytest.approx(2.68224)
    assert data.wind_dir_deg == 270
    assert data.rain_rate_mm == pytest.approx(0.762)
    assert data.rain_storm_mm == pytest.approx(3.048)
    assert data.rain_day_mm == pytest.approx(6.35)
    assert data.rain_month_mm == pytest.approx(35.56)
    assert data.rain_year_mm == pytest.approx(304.8)
    assert data.solar_radiation_wm2 == 925
    assert data.uv_index == pytest.approx(7.2)


def test_packet_parser_rejects_invalid_signature() -> None:
    packet = bytearray(make_loop_packet())
    packet[1:4] = b"BAD"

    with pytest.raises(DavisProtocolError):
        PacketParser().parse(bytes(packet))


def test_weather_data_format_round_trip() -> None:
    parser = PacketParser()
    data = WeatherData(
        temp_out_c=30.16,
        temp_in_c=24.11,
        humidity_out=68.0,
        humidity_in=45.0,
        pressure_hpa=1013.20,
        wind_speed_ms=3.57,
        wind_speed_avg_ms=2.68,
        wind_dir_deg=270,
        rain_rate_mm=0.76,
        rain_storm_mm=3.04,
        rain_day_mm=6.35,
        rain_month_mm=35.56,
        rain_year_mm=304.8,
        solar_radiation_wm2=925.0,
        uv_index=7.2,
    )

    assert parser.parse_weather_data(parser.format_weather_data(data)) == data
