"""SQLite repository for Davis WeatherLink readings."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from modbuspython.data_access.davis_weatherlink.weather_data import WeatherData
from modbuspython.data_access.logging_service import LoggingService

from .base_repository import BaseRepository

logger = LoggingService()


class DavisWeatherRepository(BaseRepository):
    """Persist decoded Davis weather readings in engineering units."""

    TABLE_NAME = "davis_weather_readings"

    WEATHER_COLUMNS = (
        "temp_out_c",
        "temp_in_c",
        "humidity_out",
        "humidity_in",
        "pressure_hpa",
        "wind_speed_ms",
        "wind_speed_avg_ms",
        "wind_dir_deg",
        "rain_rate_mm",
        "rain_storm_mm",
        "rain_day_mm",
        "rain_month_mm",
        "rain_year_mm",
        "solar_radiation_wm2",
        "uv_index",
    )

    def create_table(self) -> None:
        """Create the Davis readings table when it does not exist."""
        self.execute_command(
            """
            CREATE TABLE IF NOT EXISTS davis_weather_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                temp_out_c REAL NOT NULL,
                temp_in_c REAL NOT NULL,
                humidity_out REAL NOT NULL,
                humidity_in REAL NOT NULL,
                pressure_hpa REAL NOT NULL,
                wind_speed_ms REAL NOT NULL,
                wind_speed_avg_ms REAL NOT NULL,
                wind_dir_deg INTEGER NOT NULL,
                rain_rate_mm REAL NOT NULL,
                rain_storm_mm REAL NOT NULL,
                rain_day_mm REAL NOT NULL,
                rain_month_mm REAL NOT NULL,
                rain_year_mm REAL NOT NULL,
                solar_radiation_wm2 REAL NOT NULL,
                uv_index REAL NOT NULL,
                quality TEXT NOT NULL DEFAULT 'valid',
                source TEXT NOT NULL DEFAULT 'davis_usb',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.execute_command(
            """
            CREATE INDEX IF NOT EXISTS idx_davis_weather_readings_timestamp
            ON davis_weather_readings(timestamp)
            """
        )

    def insert_reading(
        self,
        data: WeatherData,
        timestamp: Optional[datetime] = None,
        quality: str = "valid",
        source: str = "davis_usb",
    ) -> int:
        """Store one decoded Davis reading and return the affected row count."""
        ts = timestamp or datetime.now().astimezone()
        payload = data.as_dict()
        columns = ("timestamp", *self.WEATHER_COLUMNS, "quality", "source")
        placeholders = ", ".join("?" for _ in columns)
        values = [ts.isoformat()]
        values.extend(payload[column] for column in self.WEATHER_COLUMNS)
        values.extend([quality, source])

        return self.execute_command(
            f"""
            INSERT INTO davis_weather_readings ({", ".join(columns)})
            VALUES ({placeholders})
            """,
            tuple(values),
        )

    def get_recent(self, limit: int = 500) -> List[Dict[str, Any]]:
        """Return recent Davis readings ordered from oldest to newest."""
        safe_limit = max(1, min(int(limit), 100000))
        rows = self.execute_query(
            f"""
            SELECT id, timestamp, {", ".join(self.WEATHER_COLUMNS)}, quality, source
            FROM davis_weather_readings
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (safe_limit,),
        )
        return [self._row_to_dict(row) for row in reversed(rows or [])]

    def get_for_hours(self, hours: int, max_rows: int = 2000) -> List[Dict[str, Any]]:
        """Return readings inside a recent hour window, downsampled for charts."""
        if hours <= 0:
            return self.get_recent(max_rows)
        since = datetime.now().astimezone() - timedelta(hours=int(hours))
        rows = self.execute_query(
            f"""
            SELECT id, timestamp, {", ".join(self.WEATHER_COLUMNS)}, quality, source
            FROM davis_weather_readings
            WHERE timestamp >= ?
            ORDER BY timestamp
            """,
            (since.isoformat(),),
        )
        return self._downsample([self._row_to_dict(row) for row in (rows or [])], max_rows)

    @staticmethod
    def _downsample(rows: List[Dict[str, Any]], max_rows: int) -> List[Dict[str, Any]]:
        if len(rows) <= max_rows:
            return rows
        step = len(rows) / max_rows
        sampled = [rows[int(i * step)] for i in range(max_rows)]
        if sampled[-1] != rows[-1]:
            sampled[-1] = rows[-1]
        return sampled

    def _row_to_dict(self, row) -> Dict[str, Any]:
        keys = ("id", "timestamp", *self.WEATHER_COLUMNS, "quality", "source")
        return dict(zip(keys, row))
