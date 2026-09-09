"""Unit tests for Davis WeatherLink unit conversion helpers."""

import pytest

from modbuspython.data_access.davis_weatherlink import (
    fahrenheit_to_celsius,
    inches_to_mm,
    inhg_to_hpa,
    mph_to_ms,
)
from modbuspython.data_access.davis_weatherlink.unit_conversion import celsius_to_fahrenheit


@pytest.mark.parametrize(
    ("value_f", "expected_c"),
    [
        (32.0, 0.0),
        (212.0, 100.0),
        (-40.0, -40.0),
    ],
)
def test_fahrenheit_to_celsius(value_f: float, expected_c: float) -> None:
    assert fahrenheit_to_celsius(value_f) == pytest.approx(expected_c)


def test_temperature_round_trip() -> None:
    for value_f in (-20.0, 0.0, 32.0, 77.9, 212.0):
        value_c = fahrenheit_to_celsius(value_f)
        assert celsius_to_fahrenheit(value_c) == pytest.approx(value_f, abs=0.01)


def test_mph_to_ms() -> None:
    assert mph_to_ms(0.0) == 0.0
    assert mph_to_ms(10.0) == pytest.approx(4.4704)


def test_inhg_to_hpa() -> None:
    assert inhg_to_hpa(29.921) == pytest.approx(29.921 * 33.8639)


def test_inches_to_mm() -> None:
    assert inches_to_mm(1.0) == pytest.approx(25.4)
