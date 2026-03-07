from __future__ import annotations

"""Timestamp normalization and weather station extraction utilities."""

import logging
from typing import Any, Dict, List, Optional

from ..utils_market import normalise_trade_timestamp
from ...weather_station_resolver import WeatherStationMappingError, WeatherStationResolver


def normalize_timestamp(value: Any) -> Optional[str]:
    """
    Normalize a timestamp value to ISO8601 format.

    Delegates to canonical implementation in utils_market._normalise_trade_timestamp.

    Handles:
    - Unix timestamps (seconds or milliseconds)
    - ISO8601 strings
    - Empty/None values
    - Invalid strings are passed through unchanged

    Returns None for empty/None values, original string for invalid formats.
    """
    if value in (None, ""):
        return None

    result = normalise_trade_timestamp(value)
    # If normalization failed but input was a string, pass through unchanged
    if not result and isinstance(value, str):
        return value
    return result if result else None


def select_timestamp_value(market_data: Dict[str, Any], fields: List[str]) -> Optional[object]:
    """
    Select the first non-empty timestamp value from a list of field names.

    Args:
        market_data: Market metadata dictionary
        fields: List of field names to check in order

    Returns:
        First non-empty value found, or None
    """
    for field in fields:
        value = market_data.get(field)
        if value not in (None, "", 0):
            return value
    return None


def extract_station_from_ticker(
    market_ticker: str,
    weather_resolver: WeatherStationResolver,
    logger: logging.Logger,
) -> Optional[str]:
    """
    Extract a 4-letter ICAO weather station code from a KXHIGH ticker.

    Returns ``None`` when the ticker does not encode weather data or when
    the resolver cannot map the alias.
    """
    try:
        if not market_ticker.startswith("KXHIGH"):
            return None

        station = weather_resolver.extract_station(market_ticker)
        if station:
            return station

        logger.debug("No weather station mapping found for city code in ticker: %s", market_ticker)
    except WeatherStationMappingError:  # Expected exception, returning default value  # policy_guard: allow-silent-handler
        logger.exception("Error extracting weather station from ticker %s: %s")
        return None
    else:
        return None
