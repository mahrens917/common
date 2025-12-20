"""Check preconditions for trade annotation."""

from datetime import datetime
from typing import Optional, Sequence


def should_annotate_trades(
    station_icao: Optional[str],
    is_temperature_chart: bool,
    kalshi_strikes: Optional[Sequence[float]],
    naive_timestamps: Optional[Sequence[datetime]],
) -> bool:
    """
    Determine if trade annotations should be added.

    Args:
        station_icao: Weather station identifier
        is_temperature_chart: Whether this is a temperature chart
        kalshi_strikes: Strike levels for Kalshi markets
        naive_timestamps: Timestamps for the chart

    Returns:
        True if trade annotations should be added
    """
    if not station_icao:
        return False

    if not is_temperature_chart:
        return False

    if not kalshi_strikes or not naive_timestamps:
        return False

    return True
