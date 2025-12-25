from __future__ import annotations

"""Weather station extraction logic."""


import logging
from typing import Optional

from ...weather_station_resolver import WeatherStationMappingError, WeatherStationResolver


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
