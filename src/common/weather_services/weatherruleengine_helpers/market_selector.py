from __future__ import annotations

"""Market selection logic for rule engine."""


import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional

if TYPE_CHECKING:
    from ..market_repository import MarketRepository, MarketSnapshot

from ..rule_engine_helpers import MarketEvaluator, TemperatureCoercer

logger = logging.getLogger(__name__)


class MarketSelector:
    """Handles market selection logic for rule 4 application."""

    def __init__(self, repository: MarketRepository) -> None:
        self._repository = repository

    async def select_target_market(self, city_code: str, *, day_code: Optional[str], max_temp_f: float) -> Optional[MarketSnapshot]:
        """Select best market for rule 4 application."""
        best_between, best_between_cap, best_between_floor = None, None, None
        best_greater, best_greater_floor = None, None
        best_less, best_less_cap = None, None
        async for snapshot in self._repository.iter_city_markets(city_code, day_code=day_code):
            cap, floor = MarketEvaluator.extract_strike_values(snapshot, TemperatureCoercer)
            strike_type = snapshot.strike_type.lower()

            if strike_type == "greater":
                if MarketEvaluator.evaluate_greater_market(max_temp_f, floor, snapshot, best_greater_floor):
                    best_greater = snapshot
                    best_greater_floor = floor
            elif strike_type == "less":
                if MarketEvaluator.evaluate_less_market(max_temp_f, cap, snapshot, best_less_cap):
                    best_less = snapshot
                    best_less_cap = cap
            elif strike_type == "between":
                best_between, best_between_cap, best_between_floor = MarketEvaluator.evaluate_between_market(
                    max_temp_f, cap, floor, snapshot, best_between, best_between_cap, best_between_floor
                )

        # Between markets are strictly tighter than unbounded greater/less
        if best_between is not None:
            return best_between
        if best_greater is not None:
            return best_greater
        return best_less


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
