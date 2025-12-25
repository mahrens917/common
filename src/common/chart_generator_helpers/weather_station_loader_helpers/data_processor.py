"""Process temperature data from weather tracker."""

import logging
from datetime import datetime, timezone
from typing import List, Tuple

logger = logging.getLogger("src.monitor.chart_generator")


def process_temperature_data(temperature_data: List[Tuple[int, float]], station_icao: str) -> Tuple[List[datetime], List[float]]:
    """
    Process raw temperature data into timestamps and values.

    Args:
        temperature_data: List of (timestamp_int, temperature_f) tuples
        station_icao: Station identifier for logging

    Returns:
        Tuple of (timestamps, temperatures) lists

    Raises:
        InsufficientDataError: If no valid data points remain
    """
    from datetime import datetime as dt_cls

    from common.chart_generator.exceptions import InsufficientDataError

    timestamps: List[datetime] = []
    temperatures: List[float] = []

    for timestamp_int, temperature_f in temperature_data:
        try:
            timestamp = dt_cls.fromtimestamp(timestamp_int, tz=timezone.utc)
        except (
            OverflowError,
            OSError,
            ValueError,
            TypeError,
        ) as exc:  # Best-effort cleanup operation  # policy_guard: allow-silent-handler
            logger.warning("Skipping invalid timestamp for %s: %s (%s)", station_icao, timestamp_int, exc)
            continue

        if timestamp.tzinfo is None:
            raise TypeError("Weather timestamps must be timezone-aware")

        try:
            temperatures.append(float(temperature_f))
            timestamps.append(timestamp)
        except (TypeError, ValueError):  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
            logger.warning("Skipping invalid temperature data for %s: %s", station_icao, temperature_f)

    if not timestamps or not temperatures:
        raise InsufficientDataError(f"No valid temperature data for {station_icao}")

    return timestamps, temperatures
