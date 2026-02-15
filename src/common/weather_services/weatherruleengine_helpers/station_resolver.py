from __future__ import annotations

"""Station mapping resolution logic."""

from typing import Any, Callable, Dict, Optional

from common.config.weather import WeatherConfigError, load_weather_station_mapping

from ..rule_engine_helpers import StationMappingIndexer, WeatherRuleEngineError


class StationResolver:
    """Manages station mapping and resolution."""

    def __init__(
        self,
        station_mapping_loader: Callable[[], Dict[str, Dict[str, Any]]] = load_weather_station_mapping,
    ) -> None:
        self._loader = station_mapping_loader
        self._station_mapping: Dict[str, Dict[str, Any]] = {}
        self._alias_index: Dict[str, str] = {}

    def initialize(self) -> None:
        """Load initial mapping data."""
        self._station_mapping = self._load_station_mapping()
        self._alias_index = StationMappingIndexer.build_alias_index(self._station_mapping)

    def reload_mapping(self) -> None:
        """Refresh cached mapping data from the loader."""
        self._station_mapping = self._load_station_mapping()
        self._alias_index = StationMappingIndexer.build_alias_index(self._station_mapping)

    def resolve_city_code(self, station_icao: str) -> Optional[str]:
        """Resolve station ICAO to city code."""
        return StationMappingIndexer.resolve_city_code(station_icao, self._station_mapping, self._alias_index)

    def _load_station_mapping(self) -> Dict[str, Dict[str, Any]]:
        try:
            return self._loader()
        except WeatherConfigError as exc:
            raise WeatherRuleEngineError(str(exc)) from exc
