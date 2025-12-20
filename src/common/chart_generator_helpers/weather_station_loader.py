from __future__ import annotations

"""Helper for loading weather station temperature series"""


import logging
import sys
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from common.history_tracker import WeatherHistoryTracker
from src.common.chart_generator.contexts import WeatherChartSeries
from src.common.chart_generator.exceptions import InsufficientDataError

logger = logging.getLogger("src.monitor.chart_generator")

# Minimum data points required for meaningful chart
_MIN_DATA_POINTS = 2


def _datetime_cls():
    module = sys.modules.get("src.monitor.chart_generator")
    return getattr(module, "datetime", __import__("datetime").datetime)


class WeatherStationLoader:
    """Loads temperature series data for weather stations"""

    async def load_station_temperature_series(self, station_icao: str) -> WeatherChartSeries:
        """Load and validate temperature time series for a station"""
        tracker = self._create_tracker()
        temperature_data = await self._fetch_temperature_history(tracker, station_icao)
        self._ensure_minimum_data(station_icao, temperature_data)
        timestamps, temperatures = self._parse_temperature_samples(station_icao, temperature_data)
        return self._build_chart_series(timestamps, temperatures)

    def _create_tracker(self):
        cg_module = sys.modules.get("src.monitor.chart_generator")
        tracker_cls = getattr(cg_module, "WeatherHistoryTracker", WeatherHistoryTracker)
        return tracker_cls()

    async def _fetch_temperature_history(self, tracker, station_icao: str) -> List[Tuple[int, float]]:
        try:
            await tracker.initialize()
            return await tracker.get_temperature_history(station_icao)
        finally:
            await tracker.cleanup()

    def _ensure_minimum_data(self, station_icao: str, temperature_data: List[Tuple[int, float]] | None) -> None:
        if not temperature_data:
            raise InsufficientDataError(f"No temperature data available for {station_icao}")
        if len(temperature_data) < _MIN_DATA_POINTS:
            raise InsufficientDataError(f"Insufficient temperature data for {station_icao}: {len(temperature_data)} points")

    def _parse_temperature_samples(
        self, station_icao: str, temperature_data: List[Tuple[int, float]]
    ) -> Tuple[List[datetime], List[float]]:
        timestamps: List[datetime] = []
        temperatures: List[float] = []
        for timestamp_int, temperature_f in temperature_data:
            timestamp = self._coerce_timestamp(station_icao, timestamp_int)
            if timestamp is None:
                continue
            if timestamp.tzinfo is None:
                raise TypeError("Weather timestamps must be timezone-aware")
            try:
                temperatures.append(float(temperature_f))
                timestamps.append(timestamp)
            except (TypeError, ValueError):
                logger.warning("Skipping invalid temperature data for %s: %s", station_icao, temperature_f)
        if not timestamps or not temperatures:
            raise InsufficientDataError(f"No valid temperature data for {station_icao}")
        return timestamps, temperatures

    def _coerce_timestamp(self, station_icao: str, timestamp_int: int) -> Optional[datetime]:
        try:
            return _datetime_cls().fromtimestamp(timestamp_int, tz=timezone.utc)
        except (OverflowError, OSError, ValueError, TypeError) as exc:
            logger.warning("Skipping invalid timestamp for %s: %s (%s)", station_icao, timestamp_int, exc)
            return None

    def _build_chart_series(self, timestamps: List[datetime], temperatures: List[float]) -> WeatherChartSeries:
        sorted_data = sorted(zip(timestamps, temperatures))
        timestamps_sorted, temperatures_sorted = zip(*sorted_data)
        return WeatherChartSeries(
            timestamps=list(timestamps_sorted),
            temperatures=list(temperatures_sorted),
            current_temperature=float(temperatures_sorted[-1]),
        )
