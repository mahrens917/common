"""Delegator methods mixin for KalshiTradingClient."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

if TYPE_CHECKING:
    from ..data_models.trading import OrderRequest, OrderResponse
    from ..order_execution import OrderPoller, TradeFinalizer
    from ..trading.polling_workflow import PollingOutcome


class KalshiTradingClientDelegatorMixin:
    """Mixin for delegator-backed methods.

    This mixin provides typed stub methods for dynamically delegated operations.
    The _delegator attribute should implement all methods called via delegation.
    """

    _delegator: Any

    def _build_order_poller(self) -> OrderPoller:
        return self._delegator.build_order_poller()

    def _build_trade_finalizer(self) -> TradeFinalizer:
        return self._delegator.build_trade_finalizer()

    def _apply_polling_outcome(
        self, order_response: OrderResponse, outcome: PollingOutcome
    ) -> None:
        self._delegator.apply_polling_outcome(order_response, outcome)

    def _validate_order_request(self, order_request: OrderRequest) -> None:
        self._delegator.validate_order_request(order_request)

    def _parse_order_response(
        self,
        response_data: Dict[str, Any],
        operation_name: str,
        trade_rule: str,
        trade_reason: str,
    ) -> OrderResponse:
        return self._delegator.parse_order_response(
            response_data, operation_name, trade_rule, trade_reason
        )

    def has_sufficient_balance_for_trade_with_fees(
        self, cached_balance_cents: int, trade_cost_cents: int, fees_cents: int
    ) -> bool:
        return self._delegator.has_sufficient_balance_for_trade_with_fees(
            cached_balance_cents, trade_cost_cents, fees_cents
        )

    def _create_icao_to_city_mapping(self) -> Dict[str, str]:
        return self._delegator.create_icao_to_city_mapping()

    def _extract_weather_station_from_ticker(self, market_ticker: str) -> str:
        return self._delegator.extract_weather_station_from_ticker(market_ticker)

    def _resolve_trade_context(self, market_ticker: str) -> Tuple[str, Optional[str]]:
        return self._delegator.resolve_trade_context(market_ticker)

    async def _calculate_order_fees(
        self, market_ticker: str, quantity: int, price_cents: int
    ) -> int:
        return await self._delegator.calculate_order_fees(market_ticker, quantity, price_cents)

    async def _get_trade_metadata_from_order(self, order_id: str) -> Tuple[str, str]:
        return await self._delegator.get_trade_metadata_from_order(order_id)


__all__ = ["KalshiTradingClientDelegatorMixin"]
