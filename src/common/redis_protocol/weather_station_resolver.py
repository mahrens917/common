from __future__ import annotations

"""Weather station mapping helpers dedicated to the Kalshi Redis stores."""

import logging
from typing import Any, Callable, Dict, Optional

from ..config.weather import WeatherConfigError


class WeatherStationMappingError(WeatherConfigError):
    """Raised when the weather station mapping cannot be loaded."""


class WeatherStationResolver:
    """Provide weather station lookups and alias resolution for Kalshi tickers."""

    def __init__(
        self,
        loader: Callable[[], Dict[str, Dict[str, Any]]],
        *,
        logger: logging.Logger,
    ) -> None:
        self._loader = loader
        self._logger = logger
        self._mapping: Dict[str, Dict[str, Any]] = self._load()

    @property
    def mapping(self) -> Dict[str, Dict[str, Any]]:
        return self._mapping

    def _load(self) -> Dict[str, Dict[str, Any]]:
        try:
            mapping = self._loader()
        except WeatherConfigError as exc:
            raise WeatherStationMappingError(str(exc)) from exc

        self._logger.debug("Loaded weather station mapping for %d cities", len(mapping))
        return mapping

    def reload(self) -> None:
        """Refresh the internal mapping from the configured loader."""
        self._mapping = self._load()

    def extract_station(self, market_ticker: str) -> Optional[str]:
        """
        Extract weather station ICAO code from KXHIGH market ticker with alias support.

        Args:
            market_ticker: Market ticker (e.g., KXHIGHPHIL-25AUG31-B80.5)

        Returns:
            4-letter ICAO weather station code or None if not found
        """
        if not market_ticker.startswith("KXHIGH"):
            return None

        suffix = market_ticker[len("KXHIGH") :]
        dash_index = suffix.find("-")

        if dash_index <= 0:
            self._logger.debug("No dash found in KXHIGH ticker: %s", market_ticker)
            return None

        city_code = suffix[:dash_index]

        station_data = self._mapping.get(city_code)
        if isinstance(station_data, dict) and "icao" in station_data:
            icao_code = station_data["icao"]
            self._logger.debug(
                "Extracted weather station %s from ticker %s (direct match)",
                icao_code,
                market_ticker,
            )
            return icao_code

        canonical_city_code = self._resolve_city_alias(city_code)
        if canonical_city_code:
            station_data = self._mapping.get(canonical_city_code)
            if isinstance(station_data, dict) and "icao" in station_data:
                icao_code = station_data["icao"]
                self._logger.debug(
                    "Extracted weather station %s from ticker %s (alias %s -> %s)",
                    icao_code,
                    market_ticker,
                    city_code,
                    canonical_city_code,
                )
                return icao_code

        self._logger.debug("No weather station mapping found for city code: %s", city_code)
        return None

    def _resolve_city_alias(self, city_code: str) -> Optional[str]:
        for canonical_code, station_data in self._mapping.items():
            aliases = station_data.get("aliases") or []
            if city_code in aliases:
                self._logger.debug("Resolved alias %s -> %s", city_code, canonical_code)
                return canonical_code
        return None

    def resolve_city_alias(self, city_code: str) -> Optional[str]:
        """Public alias resolution helper for callers/tests."""
        return self._resolve_city_alias(city_code)


__all__ = ["WeatherStationResolver", "WeatherStationMappingError"]
