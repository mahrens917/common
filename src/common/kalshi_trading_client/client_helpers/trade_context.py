from __future__ import annotations

"""Trade context resolution (weather stations, ICAO mapping)."""


from typing import TYPE_CHECKING, Dict, Optional, Tuple

if TYPE_CHECKING:
    from common.trading import WeatherStationResolver

    from ..services import OrderService


class TradeContextResolver:
    """Resolves trade context information."""

    @staticmethod
    def create_icao_to_city_mapping(order_service: OrderService) -> Dict[str, str]:
        """Create ICAO to city mapping."""
        return order_service.create_icao_to_city_mapping()

    @staticmethod
    def extract_weather_station_from_ticker(order_service: OrderService, market_ticker: str) -> str:
        """Extract weather station from market ticker."""
        return order_service.extract_weather_station_from_ticker(market_ticker)

    @staticmethod
    def resolve_trade_context(
        order_service: OrderService, market_ticker: str
    ) -> Tuple[str, Optional[str]]:
        """Resolve trade context from market ticker."""
        return order_service.resolve_trade_context(market_ticker)

    @staticmethod
    def get_weather_mapping(resolver: WeatherStationResolver) -> Dict[str, Dict]:
        """Get weather station mapping."""
        return resolver.mapping

    @staticmethod
    def set_weather_mapping(resolver: WeatherStationResolver, mapping: Dict[str, Dict]) -> None:
        """Set weather station mapping."""
        resolver.refresh(mapping)
