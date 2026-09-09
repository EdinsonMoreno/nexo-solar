"""Unit conversion helpers used by the Davis WeatherLink parser."""


def fahrenheit_to_celsius(value_f: float) -> float:
    """Convert Fahrenheit to Celsius."""
    return (value_f - 32.0) * 5.0 / 9.0


def celsius_to_fahrenheit(value_c: float) -> float:
    """Convert Celsius to Fahrenheit."""
    return value_c * 9.0 / 5.0 + 32.0


def mph_to_ms(value_mph: float) -> float:
    """Convert miles per hour to meters per second."""
    return value_mph * 0.44704


def inhg_to_hpa(value_inhg: float) -> float:
    """Convert inches of mercury to hectopascals."""
    return value_inhg * 33.8639


def inches_to_mm(value_inches: float) -> float:
    """Convert inches to millimeters."""
    return value_inches * 25.4
