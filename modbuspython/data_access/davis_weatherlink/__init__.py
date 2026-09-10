"""Davis WeatherLink integration primitives for Nexo Solar.

Pure parsing and validation imports stay independent from PyQt6. The threaded
reader is loaded lazily so non-UI tests can run in minimal environments.
"""

from .crc_validator import CRCValidator
from .packet_parser import PacketParser
from .transport import BaseTransport, IPTransport, SerialTransport
from .unit_conversion import fahrenheit_to_celsius, inches_to_mm, inhg_to_hpa, mph_to_ms
from .weather_data import WeatherData

__all__ = [
    "BaseTransport",
    "CRCValidator",
    "DavisWeatherLinkReader",
    "IPTransport",
    "PacketParser",
    "SerialTransport",
    "WeatherData",
    "fahrenheit_to_celsius",
    "inches_to_mm",
    "inhg_to_hpa",
    "mph_to_ms",
]


def __getattr__(name: str):
    if name == "DavisWeatherLinkReader":
        from .davis_reader import DavisWeatherLinkReader

        return DavisWeatherLinkReader
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
