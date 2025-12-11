from __future__ import annotations

"""Private methods wrapper - imports directly from canonical implementations."""

from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

from ...order_execution import OrderPoller, TradeFinalizer

if TYPE_CHECKING:
    from src.kalshi.api.client import KalshiClient

    from common.data_models.trading import OrderRequest, OrderResponse
    from common.trading import TradeStoreManager
    from common.trading.polling_workflow import PollingOutcome

    from ..services import OrderService


class PrivateMethods:
    """Encapsulates all private/internal methods."""

    def __init__(
        self,
        orders_service: OrderService,
        trade_store_manager: TradeStoreManager,
        kalshi_client: KalshiClient,
    ):
        self._orders = orders_service
        self._trade_store_manager = trade_store_manager
        self._kalshi_client = kalshi_client

    def build_order_poller(self) -> OrderPoller:
        """Build order poller."""
        return self._get_order_ops().build_order_poller(self._orders)

    def build_trade_finalizer(self) -> TradeFinalizer:
        """Build trade finalizer."""
        return self._get_order_ops().build_trade_finalizer(self._orders)

    def apply_polling_outcome(self, order_response: OrderResponse, outcome: PollingOutcome) -> None:
        """Apply polling outcome."""
        self._get_order_ops().apply_polling_outcome(self._orders, order_response, outcome)

    def validate_order_request(self, order_request: OrderRequest) -> None:
        """Validate order request."""
        self._get_order_ops().validate_order_request(self._orders, order_request)

    def _get_order_ops(self):
        from .order_operations import OrderOperations

        return OrderOperations

    def parse_order_response(self, response_data: Dict[str, Any], operation_name: str, trade_rule: str, trade_reason: str) -> OrderResponse:
        """Parse order response."""
        return self._get_order_ops().parse_order_response(self._orders, response_data, operation_name, trade_rule, trade_reason)

    def has_sufficient_balance_for_trade_with_fees(self, cached_balance_cents: int, trade_cost_cents: int, fees_cents: int) -> bool:
        """Check sufficient balance."""
        return self._get_order_ops().has_sufficient_balance_for_trade_with_fees(
            self._orders, cached_balance_cents, trade_cost_cents, fees_cents
        )

    def create_icao_to_city_mapping(self) -> Dict[str, str]:
        """Create ICAO mapping."""
        return self._get_trade_context().create_icao_to_city_mapping(self._orders)

    def extract_weather_station_from_ticker(self, market_ticker: str) -> str:
        """Extract weather station."""
        return self._get_trade_context().extract_weather_station_from_ticker(self._orders, market_ticker)

    def resolve_trade_context(self, market_ticker: str) -> Tuple[str, Optional[str]]:
        """Resolve trade context."""
        return self._get_trade_context().resolve_trade_context(self._orders, market_ticker)

    def _get_trade_context(self):
        from .trade_context import TradeContextResolver

        return TradeContextResolver

    async def calculate_order_fees(self, market_ticker: str, quantity: int, price_cents: int) -> int:
        """Calculate order fees."""
        from common.kalshi_trading_client.services.order_helpers.fee_calculator import (
            calculate_order_fees,
        )

        return await calculate_order_fees(market_ticker, quantity, price_cents)

    async def get_trade_metadata_from_order(self, order_id: str) -> tuple[str, str]:
        """Get trade metadata."""
        return await self._get_order_ops().get_trade_metadata_from_order(self._orders, order_id)

    def create_order_poller(self) -> OrderPoller:
        """Create order poller."""
        return self._get_factory_methods().create_order_poller(self._kalshi_client)

    def create_trade_finalizer(self):
        """Create trade finalizer."""
        return self._get_factory_methods().create_trade_finalizer(
            self._trade_store_manager, self._orders.resolve_trade_context, self._kalshi_client
        )

    def _get_factory_methods(self):
        from .factory_methods import FactoryMethods

        return FactoryMethods
