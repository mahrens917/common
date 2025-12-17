"""Protocol definitions for KalshiTradingClient dependency injection.

This module defines Protocol classes that establish explicit, statically-typed
interfaces for all helper modules. By using Protocols instead of dynamic
`__getattr__` delegation, pyright can verify type safety at compile time.

Usage:
    Instead of accessing private attributes dynamically:
        self._orders.create_order(request)  # reportPrivateUsage warning

    Use Protocol-typed dependencies:
        self.order_ops.create_order(request)  # Static type checking works
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Optional, Protocol, Tuple

if TYPE_CHECKING:
    from common.data_models.trading import (
        OrderRequest,
        OrderResponse,
        PortfolioBalance,
        PortfolioPosition,
    )
    from common.kalshi_api.client import KalshiClient
    from common.order_execution import OrderPoller, TradeFinalizer
    from common.trading import TradeStoreManager, WeatherStationResolver
    from common.trading.notifier_adapter import TradeNotifierAdapter
    from common.trading.polling_workflow import PollingOutcome


class IOrderService(Protocol):
    """Protocol for order service operations.

    Implementations must provide async methods for order lifecycle management.
    """

    async def create_order(self, order_request: OrderRequest) -> OrderResponse:
        """Create a new order."""
        ...

    async def complete_order_with_polling(
        self,
        order_request: OrderRequest,
        order_response: OrderResponse,
        timeout_seconds: int,
        cancel_order: Callable[[str], Awaitable[bool]],
    ) -> OrderResponse:
        """Poll for fills and finalize trade persistence after order placement."""
        ...

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order."""
        ...

    async def get_fills(self, order_id: str) -> List[Dict[str, Any]]:
        """Fetch fills for a specific order."""
        ...

    async def get_all_fills(
        self,
        min_ts: Optional[int],
        max_ts: Optional[int],
        ticker: Optional[str],
        cursor: Optional[str],
    ) -> Dict[str, Any]:
        """Fetch all fills with optional filters."""
        ...

    def validate_order_request(self, order_request: OrderRequest) -> None:
        """Validate an order request."""
        ...

    def parse_order_response(
        self,
        response_data: Dict[str, Any],
        operation_name: str,
        trade_rule: str,
        trade_reason: str,
    ) -> OrderResponse:
        """Parse raw API response into OrderResponse."""
        ...

    def build_order_poller(self) -> OrderPoller:
        """Build a new order poller instance."""
        ...

    def build_trade_finalizer(self) -> TradeFinalizer:
        """Build a new trade finalizer instance."""
        ...

    def apply_polling_outcome(self, order_response: OrderResponse, outcome: PollingOutcome) -> None:
        """Apply polling outcome to the tracked order response."""
        ...

    def update_notifier(self, notifier: TradeNotifierAdapter) -> None:
        """Propagate notifier updates to dependent helpers."""
        ...

    def update_telegram_handler(self, handler: Any) -> None:
        """Propagate Telegram handler updates to dependent helpers."""
        ...

    def create_icao_to_city_mapping(self) -> Dict[str, str]:
        """Return a copy of the resolver's ICAO -> city mapping."""
        ...

    def extract_weather_station_from_ticker(self, market_ticker: str) -> str:
        """Resolve weather station from ticker via shared resolver."""
        ...

    def resolve_trade_context(self, market_ticker: str) -> Tuple[str, Optional[str]]:
        """Determine market category and optional station for a ticker."""
        ...

    async def calculate_order_fees(self, market_ticker: str, quantity: int, price_cents: int) -> int:
        """Calculate fees for a proposed order."""
        ...

    async def get_trade_metadata_from_order(self, order_id: str) -> Tuple[str, str]:
        """Lookup stored order metadata."""
        ...


class IPortfolioService(Protocol):
    """Protocol for portfolio service operations."""

    async def get_balance(self) -> PortfolioBalance:
        """Get portfolio balance."""
        ...

    async def get_positions(self) -> List[PortfolioPosition]:
        """Get portfolio positions."""
        ...


class ITradeCollectionService(Protocol):
    """Protocol for trade collection service operations."""

    async def start(self) -> None:
        """Start trade collection."""
        ...

    async def stop(self) -> None:
        """Stop trade collection."""
        ...


class ITradeStoreOperations(Protocol):
    """Protocol for trade store operations."""

    async def get_trade_store(self, trade_store_manager: TradeStoreManager) -> Any:
        """Get the trade store."""
        ...

    async def maybe_get_trade_store(self, trade_store_manager: TradeStoreManager) -> Optional[Any]:
        """Maybe get the trade store if available."""
        ...

    async def ensure_trade_store(self, trade_store_manager: TradeStoreManager) -> Any:
        """Ensure trade store is available."""
        ...

    async def require_trade_store(self, trade_store_manager: TradeStoreManager) -> Any:
        """Require trade store, raising if unavailable."""
        ...


class IPrivateMethods(Protocol):
    """Protocol for private method operations.

    These operations are internal to the trading client but need to be
    accessible for polling workflows and order finalization.
    """

    def build_order_poller(self) -> OrderPoller:
        """Build order poller."""
        ...

    def build_trade_finalizer(self) -> TradeFinalizer:
        """Build trade finalizer."""
        ...

    def apply_polling_outcome(self, order_response: OrderResponse, outcome: PollingOutcome) -> None:
        """Apply polling outcome."""
        ...

    def validate_order_request(self, order_request: OrderRequest) -> None:
        """Validate order request."""
        ...

    def parse_order_response(self, response_data: Dict[str, Any], operation_name: str, trade_rule: str, trade_reason: str) -> OrderResponse:
        """Parse order response."""
        ...

    def has_sufficient_balance_for_trade_with_fees(self, cached_balance_cents: int, trade_cost_cents: int, fees_cents: int) -> bool:
        """Check sufficient balance."""
        ...

    def create_icao_to_city_mapping(self) -> Dict[str, str]:
        """Create ICAO mapping."""
        ...

    def extract_weather_station_from_ticker(self, market_ticker: str) -> str:
        """Extract weather station."""
        ...

    def resolve_trade_context(self, market_ticker: str) -> Tuple[str, Optional[str]]:
        """Resolve trade context."""
        ...

    async def calculate_order_fees(self, market_ticker: str, quantity: int, price_cents: int) -> int:
        """Calculate order fees."""
        ...

    async def get_trade_metadata_from_order(self, order_id: str) -> Tuple[str, str]:
        """Get trade metadata."""
        ...

    def create_order_poller(self) -> OrderPoller:
        """Create order poller."""
        ...

    def create_trade_finalizer(self) -> TradeFinalizer:
        """Create trade finalizer."""
        ...


class IPublicAPI(Protocol):
    """Protocol for public API operations.

    This is the main interface for external callers to interact with
    the trading client.
    """

    async def get_portfolio_balance(self) -> PortfolioBalance:
        """Get portfolio balance."""
        ...

    async def get_portfolio_positions(self) -> List[PortfolioPosition]:
        """Get portfolio positions."""
        ...

    async def create_order(self, order_request: OrderRequest) -> OrderResponse:
        """Create a new order."""
        ...

    async def create_order_with_polling(self, order_request: OrderRequest, timeout_seconds: int) -> OrderResponse:
        """Create order and poll for completion."""
        ...

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order."""
        ...

    async def get_fills(self, order_id: str) -> List[Dict[str, Any]]:
        """Get fills for a specific order."""
        ...

    async def get_all_fills(
        self,
        min_ts: Optional[int],
        max_ts: Optional[int],
        ticker: Optional[str],
        cursor: Optional[str],
    ) -> Dict[str, Any]:
        """Get all fills with optional filters."""
        ...

    async def start_trade_collection(self) -> bool:
        """Start trade collection."""
        ...

    async def stop_trade_collection(self) -> bool:
        """Stop trade collection."""
        ...

    async def require_trade_store(self) -> Any:
        """Require trade store."""
        ...


class ILifecycleManager(Protocol):
    """Protocol for lifecycle management operations."""

    async def initialize(self, kalshi_client: KalshiClient) -> None:
        """Initialize the trading client."""
        ...

    async def close(self, kalshi_client: KalshiClient, trade_store_manager: TradeStoreManager) -> None:
        """Close client connections."""
        ...

    def log_context_exit(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        """Log context manager exit."""
        ...


class ITradeContextResolver(Protocol):
    """Protocol for trade context resolution operations."""

    def create_icao_to_city_mapping(self, order_service: IOrderService) -> Dict[str, str]:
        """Create ICAO to city mapping."""
        ...

    def extract_weather_station_from_ticker(self, order_service: IOrderService, market_ticker: str) -> str:
        """Extract weather station from market ticker."""
        ...

    def resolve_trade_context(self, order_service: IOrderService, market_ticker: str) -> Tuple[str, Optional[str]]:
        """Resolve trade context from market ticker."""
        ...

    def get_weather_mapping(self, resolver: WeatherStationResolver) -> Dict[str, Dict[str, Any]]:
        """Get weather station mapping."""
        ...

    def set_weather_mapping(self, resolver: WeatherStationResolver, mapping: Dict[str, Dict[str, Any]]) -> None:
        """Set weather station mapping."""
        ...


class IAttributeResolver(Protocol):
    """Protocol for attribute resolution operations."""

    def resolve(self, name: str) -> Any:
        """Resolve attribute by name."""
        ...


class IOrderPollingHandler(Protocol):
    """Protocol for order polling override handling."""

    async def create_order_with_polling(
        self,
        order_request: OrderRequest,
        timeout_seconds: int,
        create_order_override: Optional[Callable[[OrderRequest], Awaitable[OrderResponse]]],
        cancel_order_override: Optional[Callable[[str], Awaitable[bool]]],
        poller_factory: Callable[[], OrderPoller],
        finalizer_factory: Callable[[], TradeFinalizer],
    ) -> OrderResponse:
        """Create order with polling, respecting overrides."""
        _ = (
            order_request,
            timeout_seconds,
            create_order_override,
            cancel_order_override,
            poller_factory,
            finalizer_factory,
        )
        raise NotImplementedError("Order polling handler must implement create_order_with_polling")


__all__ = [
    "IOrderService",
    "IPortfolioService",
    "ITradeCollectionService",
    "ITradeStoreOperations",
    "IPrivateMethods",
    "IPublicAPI",
    "ILifecycleManager",
    "ITradeContextResolver",
    "IAttributeResolver",
    "IOrderPollingHandler",
]
