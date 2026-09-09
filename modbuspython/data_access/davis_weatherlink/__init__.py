"""Davis WeatherLink integration primitives for Nexo Solar.

The package starts with pure parsing and validation code so it can be tested
without a physical station connected. Transport and threaded reader classes
will build on these modules.
"""

from .crc_validator import CRCValidator
from .packet_parser import PacketParser
from .unit_conversion import fahrenheit_to_celsius, inches_to_mm, inhg_to_hpa, mph_to_ms
from .weather_data import WeatherData

__all__ = [
    "CRCValidator",
    "PacketParser",
    "WeatherData",
    "fahrenheit_to_celsius",
    "inches_to_mm",
    "inhg_to_hpa",
    "mph_to_ms",
]
