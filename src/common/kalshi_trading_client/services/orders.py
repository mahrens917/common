from __future__ import annotations

"""
Order lifecycle helpers for the Kalshi trading client.
"""

from typing import Any, Awaitable, Callable, Dict, List

from ...data_models.trading import OrderRequest, OrderResponse
from ...order_execution import OrderPoller, TradeFinalizer
from ...trading.notifier_adapter import TradeNotifierAdapter
from ...trading.polling_workflow import PollingOutcome
from .order_helpers import OrderValidator
from .order_helpers.dependencies_factory import (
    OrderServiceDependencies,
)


class OrderService:
    """Encapsulate order placement, polling, cancellation, and metadata persistence."""

    def __init__(
        self,
        *,
        dependencies: OrderServiceDependencies,
    ) -> None:
        self._client = dependencies.kalshi_client
        self._get_trade_store = dependencies.trade_store_getter
        self._notifier = dependencies.notifier
        self._telegram_handler = dependencies.telegram_handler
        self._validator = dependencies.validator
        self._parser = dependencies.parser
        self._metadata_resolver = dependencies.metadata_resolver
        self._fee_calculator = dependencies.fee_calculator
        self._canceller = dependencies.canceller
        self._fills_fetcher = dependencies.fills_fetcher
        self._metadata_fetcher = dependencies.metadata_fetcher
        self._order_creator = dependencies.order_creator
        self._poller = dependencies.poller

    async def create_order(self, order_request: OrderRequest) -> OrderResponse:
        """Place an order and persist the associated metadata immediately."""
        return await self._order_creator.create_order(order_request)

    async def complete_order_with_polling(
        self,
        order_request: OrderRequest,
        order_response: OrderResponse,
        timeout_seconds: int,
        cancel_order: Callable[[str], Awaitable[bool]],
    ) -> OrderResponse:
        """Poll for fills and finalize trade persistence after order placement."""
        return await self._poller.complete_order_with_polling(
            order_request, order_response, timeout_seconds, cancel_order
        )

    def build_order_poller(self) -> OrderPoller:
        """Build a new order poller instance for integration tests."""
        return self._poller.poller_factory()

    def build_trade_finalizer(self) -> TradeFinalizer:
        """Build a new trade finalizer instance for integration tests."""
        return self._poller.finalizer_factory()

    def apply_polling_outcome(self, order_response: OrderResponse, outcome: PollingOutcome) -> None:
        """Apply polling outcome to the tracked order response."""
        from .order_helpers.order_poller_helpers import apply_polling_outcome as _apply

        _apply(order_response, outcome)

    def update_notifier(self, notifier: TradeNotifierAdapter) -> None:
        """Propagate notifier updates to dependent helpers."""
        self._notifier = notifier
        self._order_creator.set_notifier(notifier)

    def update_telegram_handler(self, handler: Any) -> None:
        """Propagate Telegram handler updates to dependent helpers."""
        self._telegram_handler = handler
        self._metadata_fetcher.set_telegram_handler(handler)

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order via Kalshi's REST API."""
        return await self._canceller.cancel_order(order_id)

    async def get_fills(self, order_id: str) -> List[Dict[str, Any]]:
        """Fetch fills for a specific order."""
        return await self._fills_fetcher.get_fills(order_id)

    async def get_all_fills(self, min_ts, max_ts, ticker, cursor) -> Dict[str, Any]:
        """Fetch all fills subject to optional filters."""
        return await self._fills_fetcher.get_all_fills(min_ts, max_ts, ticker, cursor)

    def validate_order_request(self, order_request: OrderRequest) -> None:
        """Verify order request payload meets trading requirements."""
        self._validator.validate_order_request(order_request)

    def parse_order_response(
        self, response_data, operation_name, trade_rule, trade_reason
    ) -> OrderResponse:
        """Strictly parse and validate a raw order response."""
        return self._parser.parse_order_response(
            response_data, operation_name, trade_rule, trade_reason
        )

    @staticmethod
    def has_sufficient_balance_for_trade_with_fees(
        cached_balance_cents, trade_cost_cents, fees_cents
    ) -> bool:
        """Determine whether cached balance covers trade cost and fees."""
        return OrderValidator.has_sufficient_balance_for_trade_with_fees(
            cached_balance_cents, trade_cost_cents, fees_cents
        )

    def create_icao_to_city_mapping(self) -> Dict[str, str]:
        """Return a copy of the resolver's ICAO -> city mapping."""
        return self._metadata_resolver.create_icao_to_city_mapping()

    def extract_weather_station_from_ticker(self, market_ticker: str) -> str:
        """Resolve weather station from ticker via shared resolver."""
        return self._metadata_resolver.extract_weather_station_from_ticker(market_ticker)

    def resolve_trade_context(self, market_ticker: str):
        """Determine market category and optional station for a ticker."""
        return self._metadata_resolver.resolve_trade_context(market_ticker)

    async def calculate_order_fees(
        self, market_ticker: str, quantity: int, price_cents: int
    ) -> int:
        """Calculate fees for a proposed order."""
        return await self._fee_calculator.calculate_order_fees(market_ticker, quantity, price_cents)

    async def get_trade_metadata_from_order(self, order_id: str):
        """Lookup stored order metadata and fail-fast when unavailable."""
        return await self._metadata_fetcher.get_trade_metadata_from_order(order_id)


async def _create_order(self, order_request: OrderRequest) -> OrderResponse:
    """Place an order and persist the associated metadata immediately."""
    return await self._order_creator.create_order(order_request)


async def _complete_order_with_polling(
    self,
    order_request: OrderRequest,
    order_response: OrderResponse,
    timeout_seconds: int,
    cancel_order: Callable[[str], Awaitable[bool]],
) -> OrderResponse:
    """Poll for fills and finalise trade persistence after order placement."""
    return await self._poller.complete_order_with_polling(
        order_request, order_response, timeout_seconds, cancel_order
    )


def _build_order_poller(self) -> OrderPoller:
    return self._poller.poller_factory()


def _build_trade_finalizer(self) -> TradeFinalizer:
    return self._poller.finalizer_factory()


def _update_notifier(self, notifier: TradeNotifierAdapter) -> None:
    self._notifier = notifier
    self._order_creator.set_notifier(notifier)


def _update_telegram_handler(self, handler) -> None:
    self._telegram_handler = handler
    self._metadata_fetcher.set_telegram_handler(handler)


async def _cancel_order(self, order_id: str) -> bool:
    """Cancel a pending order via Kalshi's REST API."""
    return await self._canceller.cancel_order(order_id)


async def _get_fills(self, order_id: str) -> List[Dict[str, Any]]:
    """Fetch fills for a specific order."""
    return await self._fills_fetcher.get_fills(order_id)


async def _get_all_fills(self, min_ts, max_ts, ticker, cursor) -> Dict[str, Any]:
    """Fetch all fills subject to optional filters."""
    return await self._fills_fetcher.get_all_fills(min_ts, max_ts, ticker, cursor)


def _validate_order_request(self, order_request: OrderRequest) -> None:
    """Verify order request payload meets trading requirements."""
    self._validator.validate_order_request(order_request)


def _parse_order_response(self, response_data, operation_name, trade_rule, trade_reason):
    """Strictly parse and validate a raw order response."""
    return self._parser.parse_order_response(
        response_data, operation_name, trade_rule, trade_reason
    )


def _has_sufficient_balance_for_trade_with_fees(
    cached_balance_cents, trade_cost_cents, fees_cents
) -> bool:
    """Determine whether cached balance covers trade cost and fees."""
    return OrderValidator.has_sufficient_balance_for_trade_with_fees(
        cached_balance_cents, trade_cost_cents, fees_cents
    )


def _create_icao_to_city_mapping(self) -> Dict[str, str]:
    """Return a copy of the resolver's ICAO -> city mapping."""
    return self._metadata_resolver.create_icao_to_city_mapping()


def _extract_weather_station_from_ticker(self, market_ticker: str) -> str:
    """Resolve weather station from ticker via shared resolver."""
    return self._metadata_resolver.extract_weather_station_from_ticker(market_ticker)


def _resolve_trade_context(self, market_ticker: str):
    """Determine market category and optional station for a ticker."""
    return self._metadata_resolver.resolve_trade_context(market_ticker)


async def _calculate_order_fees(self, market_ticker: str, quantity: int, price_cents: int) -> int:
    """Calculate fees for a proposed order."""
    return await self._fee_calculator.calculate_order_fees(market_ticker, quantity, price_cents)


async def _get_trade_metadata_from_order(self, order_id: str):
    """Lookup stored order metadata and fail-fast when unavailable."""
    return await self._metadata_fetcher.get_trade_metadata_from_order(order_id)


__all__ = ["OrderService"]
