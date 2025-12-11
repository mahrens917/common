from __future__ import annotations

"""
Helper operations for OrderService to reduce class size.
"""

from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from .fee_calculator import FeeCalculator
    from .fills_fetcher import FillsFetcher
    from .metadata_fetcher import MetadataFetcher
    from .metadata_resolver import MetadataResolver
    from .order_canceller import OrderCanceller
    from .order_parser import OrderParser
    from .order_validator import OrderValidator


class ValidationOperations:
    """Handles order validation and parsing operations."""

    def __init__(self, validator: "OrderValidator", parser: "OrderParser"):
        self._validator = validator
        self._parser = parser

    def validate_order_request(self, order_request) -> None:
        """Verify order request payload meets trading requirements."""
        self._validator.validate_order_request(order_request)

    def parse_order_response(self, response_data, operation_name, trade_rule, trade_reason):
        """Strictly parse and validate a raw order response."""
        return self._parser.parse_order_response(response_data, operation_name, trade_rule, trade_reason)

    @staticmethod
    def has_sufficient_balance_for_trade_with_fees(cached_balance_cents, trade_cost_cents, fees_cents) -> bool:
        """Determine whether cached balance covers trade cost and fees."""
        from .order_validator import OrderValidator

        return OrderValidator.has_sufficient_balance_for_trade_with_fees(cached_balance_cents, trade_cost_cents, fees_cents)


class FillsOperations:
    """Handles order cancellation and fills fetching."""

    def __init__(self, canceller: "OrderCanceller", fills_fetcher: "FillsFetcher"):
        self._canceller = canceller
        self._fills_fetcher = fills_fetcher

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order via Kalshi's REST API."""
        return await self._canceller.cancel_order(order_id)

    async def get_fills(self, order_id: str) -> List[Dict[str, Any]]:
        """Fetch fills for a specific order."""
        return await self._fills_fetcher.get_fills(order_id)

    async def get_all_fills(self, min_ts, max_ts, ticker, cursor) -> Dict[str, Any]:
        """Fetch all fills subject to optional filters."""
        return await self._fills_fetcher.get_all_fills(min_ts, max_ts, ticker, cursor)


class MetadataOperations:
    """Handles trade metadata and context resolution."""

    def __init__(
        self,
        metadata_resolver: "MetadataResolver",
        fee_calculator: "FeeCalculator",
        metadata_fetcher: "MetadataFetcher",
    ):
        self._metadata_resolver = metadata_resolver
        self._fee_calculator = fee_calculator
        self._metadata_fetcher = metadata_fetcher

    def create_icao_to_city_mapping(self) -> Dict[str, str]:
        """Return a copy of the resolver's ICAO -> city mapping."""
        return self._metadata_resolver.create_icao_to_city_mapping()

    def extract_weather_station_from_ticker(self, market_ticker: str) -> str:
        """Resolve weather station from ticker via shared resolver."""
        return self._metadata_resolver.extract_weather_station_from_ticker(market_ticker)

    def resolve_trade_context(self, market_ticker: str):
        """Determine market category and optional station for a ticker."""
        return self._metadata_resolver.resolve_trade_context(market_ticker)

    async def calculate_order_fees(self, market_ticker: str, quantity: int, price_cents: int) -> int:
        """Calculate fees for a proposed order."""
        return await self._fee_calculator.calculate_order_fees(market_ticker, quantity, price_cents)

    async def get_trade_metadata_from_order(self, order_id: str):
        """Lookup stored order metadata and fail-fast when unavailable."""
        return await self._metadata_fetcher.get_trade_metadata_from_order(order_id)

    def update_telegram_handler(self, handler):
        """Update telegram handler in metadata fetcher."""
        self._metadata_fetcher.set_telegram_handler(handler)
