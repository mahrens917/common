"""Helper components for weather rule engine."""

import logging
from datetime import datetime
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

logger = logging.getLogger(__name__)


class WeatherRuleEngineError(RuntimeError):
    """Raised when rule evaluation cannot proceed."""

    def __init__(self, message: str = "Weather rule engine not configured") -> None:
        super().__init__(message)
        self.message = message


class StationCityMappingMissingError(WeatherRuleEngineError):
    """Raised when the rule engine cannot resolve a station's city code."""

    def __init__(self, station_icao: str) -> None:
        super().__init__(f"No city mapping found for station {station_icao}")


class ZoneInfoUnavailableError(WeatherRuleEngineError):
    """ZoneInfo database missing required timezone."""

    def __init__(self, zone_name: str) -> None:
        super().__init__(f"ZoneInfo database does not include '{zone_name}'")


class DayCodeFormatError(WeatherRuleEngineError):
    """Raised when Kalshi-compatible day code cannot be formatted."""

    def __init__(self) -> None:
        super().__init__("Failed to format weather day code")


class InvalidTemperatureValueError(WeatherRuleEngineError):
    """Raised when temperature text cannot be parsed."""

    def __init__(self, raw_value: Any) -> None:
        super().__init__(f"Invalid temperature value {raw_value!r}")


class UnsupportedTemperatureTypeError(WeatherRuleEngineError):
    """Raised when temperature coercion receives an unsupported type."""

    def __init__(self, value_type: type) -> None:
        super().__init__(f"Unsupported temperature type: {value_type!r}")


class InvalidMaxTemperatureError(WeatherRuleEngineError):
    """Raised when station max_temp_f payloads are invalid."""

    def __init__(self, station_icao: str) -> None:
        super().__init__(f"Invalid max_temp_f for station {station_icao}")


class MissingMaxTemperatureError(WeatherRuleEngineError):
    """Raised when station max_temp_f payloads are absent."""

    def __init__(self, station_icao: str) -> None:
        super().__init__(f"Missing required max_temp_f field for station {station_icao}")


class InvalidStrikeMetadataError(WeatherRuleEngineError):
    """Raised when market snapshots contain malformed strike values."""

    def __init__(self, market_key: str) -> None:
        super().__init__(f"Invalid strike metadata for market {market_key}")


class MissingGreaterFloorStrikeError(WeatherRuleEngineError):
    """Raised when 'greater' markets lack floor strike data."""

    def __init__(self, market_key: str) -> None:
        super().__init__(f"Market {market_key} missing floor strike for 'greater' evaluation")


class MissingLessCapStrikeError(WeatherRuleEngineError):
    """Raised when 'less' markets lack cap strike data."""

    def __init__(self, market_key: str) -> None:
        super().__init__(f"Market {market_key} missing cap strike for 'less' evaluation")


class MissingBetweenStrikeError(WeatherRuleEngineError):
    """Raised when 'between' markets lack cap/floor strike data."""

    def __init__(self, market_key: str) -> None:
        super().__init__(f"Market {market_key} missing cap/floor strikes for 'between' evaluation")


class TemperatureCoercer:
    """Coerce various types to float temperature values."""

    @staticmethod
    def coerce(value: Any) -> Optional[float]:
        """Convert value to float temperature or None."""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            text = value.strip()
            if not text or text.lower() == "none":
                return None
            try:
                return float(text)
            except ValueError as exc:
                raise InvalidTemperatureValueError(value) from exc
        raise UnsupportedTemperatureTypeError(type(value))


class DayCodeBuilder:
    """Build Kalshi-compatible day codes (e.g., 25JAN01)."""

    @staticmethod
    def build() -> str:
        """Generate day code from current Eastern time."""
        try:
            eastern = ZoneInfo("America/New_York")
        except ZoneInfoNotFoundError as exc:
            raise ZoneInfoUnavailableError("America/New_York") from exc

        now_et = datetime.now(eastern)
        try:
            return f"{str(now_et.year)[-2:]}{now_et.strftime('%b').upper()}{now_et.day:02d}"
        except (ValueError, TypeError) as exc:
            raise DayCodeFormatError() from exc


class StationMappingIndexer:
    """Build and maintain indices for station aliases."""

    @staticmethod
    def build_alias_index(mapping: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
        """Create alias -> city_code index."""
        alias_index: Dict[str, str] = {}
        for city_code, station_data in mapping.items():
            aliases_val = station_data.get("aliases")
            if aliases_val:
                aliases_list = aliases_val
            else:
                aliases_list = []
            for alias in aliases_list:
                alias_index[alias] = city_code
        return alias_index

    @staticmethod
    def resolve_city_code(station_icao: str, mapping: Dict[str, Dict[str, Any]], alias_index: Dict[str, str]) -> Optional[str]:
        """Find city code from station ICAO, checking direct and alias lookup."""
        for city_code, station_data in mapping.items():
            if station_data.get("icao") == station_icao:
                return city_code
        return alias_index.get(station_icao)


class TemperatureExtractor:
    """Extract temperature from weather data with validation."""

    @staticmethod
    def extract_max_temp(weather_data: Dict[str, Any], station_icao: str) -> float:
        """Get max_temp_f field, raising if missing."""
        try:
            value = TemperatureCoercer.coerce(weather_data.get("max_temp_f"))
        except (InvalidTemperatureValueError, UnsupportedTemperatureTypeError) as exc:
            raise InvalidMaxTemperatureError(station_icao) from exc

        if value is None:
            raise MissingMaxTemperatureError(station_icao)
        return value


class MarketSelectionHelper:
    """Helper for selecting appropriate markets based on temperature data."""

    @staticmethod
    def is_temperature_in_band(temp_f: float, floor: Optional[float], cap: Optional[float]) -> bool:
        """Check if temperature is within specified bounds."""
        if floor is None or cap is None:
            return False
        return floor <= temp_f < cap

    @staticmethod
    def calculate_market_width(floor: Optional[float], cap: Optional[float]) -> Optional[float]:
        """Calculate market band width."""
        if floor is None or cap is None:
            return None
        return cap - floor


class MarketEvaluator:
    """Evaluate and select markets based on strikes and temperature."""

    @staticmethod
    def extract_strike_values(snapshot, temperature_coercer) -> tuple:
        """Extract and validate cap/floor strike."""
        try:
            cap = temperature_coercer.coerce(snapshot.data.get("cap_strike"))
            floor = temperature_coercer.coerce(snapshot.data.get("floor_strike"))
        except (InvalidTemperatureValueError, UnsupportedTemperatureTypeError) as exc:
            raise InvalidStrikeMetadataError(snapshot.key) from exc
        else:
            return cap, floor

    @staticmethod
    def evaluate_greater_market(max_temp_f, floor, snapshot, best_floor):
        """Check if greater market qualifies."""
        if floor is None:
            raise MissingGreaterFloorStrikeError(snapshot.key)
        return max_temp_f >= floor and (best_floor is None or floor > best_floor)

    @staticmethod
    def evaluate_less_market(max_temp_f, cap, snapshot, best_cap):
        """Check if less market qualifies (tightest cap above temp wins)."""
        if cap is None:
            raise MissingLessCapStrikeError(snapshot.key)
        return max_temp_f < cap and (best_cap is None or cap < best_cap)

    @staticmethod
    def evaluate_between_market(
        max_temp_f,
        cap,
        floor,
        snapshot,
        best_snapshot,
        best_cap,
        best_floor,
    ):
        """Evaluate between market and return best selection."""
        if cap is None or floor is None:
            raise MissingBetweenStrikeError(snapshot.key)

        if not MarketSelectionHelper.is_temperature_in_band(max_temp_f, floor, cap):
            return best_snapshot, best_cap, best_floor

        # When no previous best snapshot, use current snapshot
        selected_snapshot = snapshot
        selected_cap = cap
        selected_floor = floor

        if best_snapshot is not None:
            current_width = MarketSelectionHelper.calculate_market_width(floor, cap)
            best_width = MarketSelectionHelper.calculate_market_width(best_floor, best_cap)

            if current_width is None or best_width is None or current_width >= best_width:
                selected_snapshot = best_snapshot
                selected_cap = best_cap
                selected_floor = best_floor

        return selected_snapshot, selected_cap, selected_floor
