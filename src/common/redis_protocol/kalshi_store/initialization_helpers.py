"""
Initialization helpers for KalshiStore - Weather resolver and setup.

Extracts initialization logic to reduce KalshiStore class size.
"""

import logging
from typing import TYPE_CHECKING

from ...config.weather import WeatherConfigError
from ..weather_station_resolver import WeatherStationResolver

if TYPE_CHECKING:
    from typing import Callable


def build_weather_resolver(loader: "Callable", logger: logging.Logger) -> WeatherStationResolver:  # pragma: no cover
    """Build weather station resolver with error handling."""
    try:
        return WeatherStationResolver(loader, logger=logger)
    except WeatherConfigError:
        logger.exception("Weather resolver initialization failed")
        raise
    except (RuntimeError, ValueError, OSError, KeyError, TypeError) as exc:
        logger.exception("Unexpected error building weather resolver")
        raise WeatherConfigError("Weather resolver construction failed") from exc
