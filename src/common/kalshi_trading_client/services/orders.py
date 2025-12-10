from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, List

from ...data_models.trading import OrderRequest, OrderResponse
from ...order_execution import OrderPoller, TradeFinalizer
from ...trading.notifier_adapter import TradeNotifierAdapter
from ...trading.polling_workflow import PollingOutcome
from .order_helpers import OrderValidator
from .order_helpers.dependencies_factory import OrderServiceDependencies


class OrderService:
    def __init__(self, *, dependencies: OrderServiceDependencies) -> None:
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
        return await self._order_creator.create_order(order_request)

    async def complete_order_with_polling(
        self,
        order_request: OrderRequest,
        order_response: OrderResponse,
        timeout_seconds: int,
        cancel_order: Callable[[str], Awaitable[bool]],
    ) -> OrderResponse:
        return await self._poller.complete_order_with_polling(
            order_request, order_response, timeout_seconds, cancel_order
        )

    def build_order_poller(self) -> OrderPoller:
        return self._poller.poller_factory()

    def build_trade_finalizer(self) -> TradeFinalizer:
        return self._poller.finalizer_factory()

    def apply_polling_outcome(self, order_response: OrderResponse, outcome: PollingOutcome) -> None:
        from .order_helpers.order_poller_helpers import apply_polling_outcome as _apply

        _apply(order_response, outcome)

    def update_notifier(self, notifier: TradeNotifierAdapter) -> None:
        self._notifier = notifier
        self._order_creator.set_notifier(notifier)

    def update_telegram_handler(self, handler: Any) -> None:
        self._telegram_handler = handler
        self._metadata_fetcher.set_telegram_handler(handler)

    async def cancel_order(self, order_id: str) -> bool:
        return await self._canceller.cancel_order(order_id)

    async def get_fills(self, order_id: str) -> List[Dict[str, Any]]:
        return await self._fills_fetcher.get_fills(order_id)

    async def get_all_fills(self, min_ts, max_ts, ticker, cursor) -> Dict[str, Any]:
        return await self._fills_fetcher.get_all_fills(min_ts, max_ts, ticker, cursor)

    def validate_order_request(self, order_request: OrderRequest) -> None:
        self._validator.validate_order_request(order_request)

    def parse_order_response(
        self, response_data, operation_name, trade_rule, trade_reason
    ) -> OrderResponse:
        return self._parser.parse_order_response(
            response_data, operation_name, trade_rule, trade_reason
        )

    @staticmethod
    def has_sufficient_balance_for_trade_with_fees(
        cached_balance_cents, trade_cost_cents, fees_cents
    ) -> bool:
        return OrderValidator.has_sufficient_balance_for_trade_with_fees(
            cached_balance_cents, trade_cost_cents, fees_cents
        )

    def create_icao_to_city_mapping(self) -> Dict[str, str]:
        return self._metadata_resolver.create_icao_to_city_mapping()

    def extract_weather_station_from_ticker(self, market_ticker: str) -> str:
        return self._metadata_resolver.extract_weather_station_from_ticker(market_ticker)

    def resolve_trade_context(self, market_ticker: str):
        return self._metadata_resolver.resolve_trade_context(market_ticker)

    async def calculate_order_fees(
        self, market_ticker: str, quantity: int, price_cents: int
    ) -> int:
        return await self._fee_calculator.calculate_order_fees(market_ticker, quantity, price_cents)

    async def get_trade_metadata_from_order(self, order_id: str):
        return await self._metadata_fetcher.get_trade_metadata_from_order(order_id)


__all__ = ["OrderService"]
