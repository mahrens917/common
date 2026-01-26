from __future__ import annotations

"""Weather rule evaluation shared between tracker and updater."""

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from common.config.weather import WeatherConfigError, load_weather_station_mapping

from .market_repository import MarketRepository, MarketSnapshot
from .rule_engine_helpers import (
    DayCodeBuilder,
    InvalidTemperatureValueError,
    MarketEvaluator,
    StationCityMappingMissingError,
    StationMappingIndexer,
    TemperatureCoercer,
    TemperatureExtractor,
    UnsupportedTemperatureTypeError,
    WeatherRuleEngineError,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MidpointSignalResult:
    """Metadata describing a Rule 4 midpoint signal application."""

    station_icao: str
    market_key: str
    ticker: str
    max_temp_f: float
    explanation: str


class WeatherRuleEngine:
    """Evaluate and publish weather trading rules via an injected repository."""

    def __init__(
        self,
        repository: MarketRepository,
        *,
        station_mapping_loader: Callable[[], Dict[str, Dict[str, Any]]] = load_weather_station_mapping,
    ) -> None:
        self._repository = repository
        self._station_mapping_loader = station_mapping_loader or load_weather_station_mapping
        self._station_mapping = self._load_station_mapping()
        self._alias_index = StationMappingIndexer.build_alias_index(self._station_mapping)

    async def apply_midpoint_signal(self, station_icao: str) -> Optional[MidpointSignalResult]:
        weather_data = await self._repository.get_weather_data(station_icao)
        if not weather_data:
            logger.debug("WeatherRuleEngine: No weather data available for %s", station_icao)
            return None
        max_temp_f = TemperatureExtractor.extract_max_temp(weather_data, station_icao)
        city_code = self._resolve_city_code(station_icao)
        if not city_code:
            raise StationCityMappingMissingError(station_icao)
        day_code = DayCodeBuilder.build()
        target_snapshot = await self._select_target_market(city_code, day_code=day_code, max_temp_f=max_temp_f)
        if not target_snapshot:
            logger.info(
                "WeatherRuleEngine: No Rule 4 market found for %s at %.1f°F",
                station_icao,
                max_temp_f,
            )
            return None
        return await self._apply_market_fields_and_return_result(target_snapshot, station_icao, max_temp_f)

    def reload_station_mapping(self) -> None:
        self._station_mapping = self._load_station_mapping()
        self._alias_index = StationMappingIndexer.build_alias_index(self._station_mapping)

    def _load_station_mapping(self) -> Dict[str, Dict[str, Any]]:
        try:
            return self._station_mapping_loader()
        except WeatherConfigError as exc:
            raise WeatherRuleEngineError(str(exc)) from exc

    def _resolve_city_code(self, station_icao: str) -> Optional[str]:
        return StationMappingIndexer.resolve_city_code(station_icao, self._station_mapping, self._alias_index)

    async def _select_target_market(self, city_code: str, *, day_code: Optional[str], max_temp_f: float) -> Optional[MarketSnapshot]:
        best_snapshot, best_cap, best_floor = None, None, None
        async for snapshot in self._repository.iter_city_markets(city_code, day_code=day_code):
            cap, floor = MarketEvaluator.extract_strike_values(snapshot, TemperatureCoercer)
            strike_type = snapshot.strike_type.lower()
            if strike_type == "greater":
                if MarketEvaluator.evaluate_greater_market(max_temp_f, floor, snapshot, best_floor):
                    best_snapshot = snapshot
                    best_cap = cap
                    best_floor = floor
                continue
            if strike_type == "between":
                best_snapshot, best_cap, best_floor = MarketEvaluator.evaluate_between_market(
                    max_temp_f, cap, floor, snapshot, best_snapshot, best_cap, best_floor
                )
        return best_snapshot

    async def _apply_market_fields_and_return_result(
        self, target_snapshot: MarketSnapshot, station_icao: str, max_temp_f: float
    ) -> MidpointSignalResult:
        explanation = f"⏰ MIDPOINT: Taking {max_temp_f}°F as final high → Buying YES"
        await self._repository.set_market_fields(
            target_snapshot.key,
            {
                "t_ask": "99",
                "weather_explanation": explanation,
                "last_rule_applied": "rule_4",
                "intended_action": "BUY",
                "intended_side": "YES",
                "rule_triggered": "rule_4",
            },
        )
        logger.info(
            "WeatherRuleEngine: Rule 4 applied to %s for station %s",
            target_snapshot.ticker,
            station_icao,
        )
        return MidpointSignalResult(
            station_icao=station_icao,
            market_key=target_snapshot.key,
            ticker=target_snapshot.ticker,
            max_temp_f=max_temp_f,
            explanation=explanation,
        )

    @staticmethod
    def _coerce_temperature(value: Any) -> Optional[float]:
        try:
            return TemperatureCoercer.coerce(value)
        except (InvalidTemperatureValueError, UnsupportedTemperatureTypeError) as exc:
            raise ValueError(str(exc)) from exc


__all__ = [
    "WeatherRuleEngine",
    "WeatherRuleEngineError",
    "MidpointSignalResult",
    "load_weather_station_mapping",
]
