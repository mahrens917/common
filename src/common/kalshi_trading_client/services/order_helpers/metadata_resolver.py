"""Trade metadata and context resolution."""

import logging
from typing import Dict, Optional, Tuple

from ....exceptions import ValidationError
from ....redis_schema import describe_kalshi_ticker
from ....redis_schema.markets import KalshiMarketCategory

logger = logging.getLogger(__name__)


class MetadataResolver:
    """Resolve trade metadata and context from tickers."""

    def __init__(self, weather_resolver):
        self._weather_resolver = weather_resolver

    def create_icao_to_city_mapping(self) -> Dict[str, str]:
        """Return a copy of the resolver's ICAO -> city mapping."""
        return self._weather_resolver.icao_to_city_map.copy()

    def extract_weather_station_from_ticker(self, market_ticker: str) -> str:
        """Resolve weather station from ticker via shared resolver."""
        try:
            return self._weather_resolver.resolve_ticker(market_ticker)
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc

    def resolve_trade_context(self, market_ticker: str) -> Tuple[str, Optional[str]]:
        """Determine market category and optional station for a ticker."""
        descriptor = describe_kalshi_ticker(market_ticker)
        category = descriptor.category.value
        weather_station: Optional[str] = None

        if descriptor.category == KalshiMarketCategory.WEATHER:
            weather_station = self.extract_weather_station_from_ticker(descriptor.ticker)

        return category, weather_station
