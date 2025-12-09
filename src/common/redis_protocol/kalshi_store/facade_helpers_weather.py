"""Weather-related methods for facade helpers."""

from typing import Any, Optional


def resolve_weather_station_from_ticker(
    market_ticker: str,
    *,
    writer: Any,
    weather_resolver: Any,
) -> Optional[str]:
    """
    Resolve weather station via writer.

    Centralizes the common delegator logic for extracting weather station
    from market ticker.
    """
    return writer._extract_weather_station_from_ticker(market_ticker)
