"""
Utility delegation for KalshiStore - Descriptor operations and aggregation.

Extracts private utility methods from KalshiStore to reduce class size.
"""

from typing import Any, Dict, Iterable, List, Optional, Tuple

from ...redis_schema import KalshiMarketDescriptor, describe_kalshi_ticker
from ..weather_station_resolver import WeatherStationResolver
from .facade_helpers_weather import resolve_weather_station_from_ticker
from .reader import KalshiMarketReader
from .writer import KalshiMarketWriter


class UtilityDelegator:
    """Delegates descriptor, extraction, and aggregation operations."""

    def __init__(
        self,
        writer: KalshiMarketWriter,
        reader: KalshiMarketReader,
        weather_resolver: WeatherStationResolver,
    ) -> None:
        self._writer = writer
        self._reader = reader
        self.weather_resolver = weather_resolver

    def market_descriptor(self, market_ticker: str) -> KalshiMarketDescriptor:
        """Get market descriptor from ticker."""
        return describe_kalshi_ticker(market_ticker)

    def extract_weather_station_from_ticker(self, market_ticker: str) -> Optional[str]:
        """Extract weather station ICAO code from market ticker."""
        return resolve_weather_station_from_ticker(market_ticker, writer=self._writer, weather_resolver=self.weather_resolver)

    def derive_expiry_iso(self, market_ticker: str, metadata: Dict[str, Any]) -> str:
        """Derive ISO expiry date from market ticker and metadata."""
        descriptor = self.market_descriptor(market_ticker)
        return self._writer.derive_expiry_iso(market_ticker, metadata, descriptor)

    def ensure_market_metadata_fields(self, market_ticker: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure all required metadata fields are present."""
        return self._reader.ensure_market_metadata_fields(market_ticker, metadata)

    def aggregate_markets_by_point(
        self, markets: Iterable[Dict[str, Any]]
    ) -> Tuple[Dict[Tuple[str, float, str], List[str]], Dict[str, Dict[str, Any]]]:
        """Group markets by strike price and expiry."""
        return self._reader.aggregate_markets_by_point(list(markets))

    def build_strike_summary(
        self,
        grouped: Dict[Tuple[str, float, str], List[str]],
        market_by_ticker: Dict[str, Dict[str, Any]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Build strike summary from grouped markets."""
        return self._reader.build_strike_summary(grouped, market_by_ticker)
