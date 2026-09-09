"""Data model for decoded Davis WeatherLink readings."""

from dataclasses import asdict, dataclass
from typing import Dict


@dataclass(frozen=True)
class WeatherData:
    """Weather values decoded from a Davis LOOP packet in engineering units."""

    temp_out_c: float
    temp_in_c: float
    humidity_out: float
    humidity_in: float
    pressure_hpa: float
    wind_speed_ms: float
    wind_speed_avg_ms: float
    wind_dir_deg: int
    rain_rate_mm: float
    rain_storm_mm: float
    rain_day_mm: float
    rain_month_mm: float
    rain_year_mm: float
    solar_radiation_wm2: float
    uv_index: float

    def as_dict(self) -> Dict[str, float]:
        """Return the reading as a plain dictionary for UI bridges or storage."""
        return asdict(self)
