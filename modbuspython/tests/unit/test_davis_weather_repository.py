"""Tests for persisted Davis WeatherLink readings."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from modbuspython.data_access.davis_weatherlink import WeatherData
from modbuspython.data_access.repositories.davis_weather_repository import DavisWeatherRepository


def make_weather_data(solar: float = 83.0) -> WeatherData:
    return WeatherData(
        temp_out_c=26.9,
        temp_in_c=29.6,
        humidity_out=81.0,
        humidity_in=42.0,
        pressure_hpa=1007.1,
        wind_speed_ms=0.0,
        wind_speed_avg_ms=0.0,
        wind_dir_deg=189,
        rain_rate_mm=0.0,
        rain_storm_mm=0.0,
        rain_day_mm=0.0,
        rain_month_mm=0.0,
        rain_year_mm=0.0,
        solar_radiation_wm2=solar,
        uv_index=0.5,
    )


def test_davis_repository_create_table_starts_empty(tmp_path) -> None:
    repo = DavisWeatherRepository(str(tmp_path / "nexo_solar.db"), use_pool=False)

    repo.create_table()

    assert repo.get_recent() == []


def test_davis_repository_creates_table_and_stores_all_weather_fields(tmp_path) -> None:
    repo = DavisWeatherRepository(str(tmp_path / "nexo_solar.db"), use_pool=False)
    repo.create_table()

    repo.insert_reading(
        make_weather_data(),
        timestamp=datetime(2026, 9, 10, 6, 45, 17, tzinfo=timezone.utc),
        source="davis_usb",
    )

    rows = repo.get_recent()

    assert len(rows) == 1
    row = rows[0]
    assert row["timestamp"] == "2026-09-10T06:45:17+00:00"
    assert row["source"] == "davis_usb"
    assert row["quality"] == "valid"
    assert row["solar_radiation_wm2"] == 83.0
    assert row["temp_out_c"] == 26.9
    assert row["humidity_out"] == 81.0
    assert row["pressure_hpa"] == 1007.1
    assert row["wind_dir_deg"] == 189
    assert row["uv_index"] == 0.5


def test_davis_repository_returns_recent_rows_from_oldest_to_newest(tmp_path) -> None:
    repo = DavisWeatherRepository(str(tmp_path / "nexo_solar.db"), use_pool=False)
    repo.create_table()
    repo.insert_reading(make_weather_data(80), timestamp=datetime(2026, 9, 10, 6, 0, tzinfo=timezone.utc))
    repo.insert_reading(make_weather_data(120), timestamp=datetime(2026, 9, 10, 7, 0, tzinfo=timezone.utc))
    repo.insert_reading(make_weather_data(160), timestamp=datetime(2026, 9, 10, 8, 0, tzinfo=timezone.utc))

    rows = repo.get_recent(limit=2)

    assert [row["solar_radiation_wm2"] for row in rows] == [120.0, 160.0]


def test_davis_repository_filters_recent_hours_and_downsamples(tmp_path) -> None:
    repo = DavisWeatherRepository(str(tmp_path / "nexo_solar.db"), use_pool=False)
    repo.create_table()
    now = datetime.now(timezone.utc)
    for index in range(10):
        timestamp = now - timedelta(days=1) if index == 0 else now + timedelta(seconds=index)
        repo.insert_reading(make_weather_data(index), timestamp=timestamp)

    rows = repo.get_for_hours(hours=1, max_rows=3)

    assert len(rows) == 3
    assert rows[-1]["solar_radiation_wm2"] == 9.0
