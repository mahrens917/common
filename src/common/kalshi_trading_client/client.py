from __future__ import annotations

"""High-level Kalshi trading client - Protocol-based typed coordinator.

This module has been refactored to use Protocol-typed composition instead of
dynamic __getattr__ delegation. This eliminates reportAttributeAccessIssue
and reportPrivateUsage warnings from pyright.
"""

import logging
from typing import Any, Dict, Optional

from common.kalshi_api.client import KalshiClient

from ..data_models.trading import OrderRequest, OrderResponse
from ..order_execution import OrderPoller, TradeFinalizer
from ..redis_protocol.trade_store import TradeStore
from ..trading import WeatherStationResolver
from .client_api_mixin import (
    KalshiTradingClientAPIMixin,
    KalshiTradingClientTradeStoreMixin,
)
from .client_delegator_mixin import KalshiTradingClientDelegatorMixin
from .client_helpers import (
    ClientInitializer,
    LifecycleManager,
    OrderPollingOverrideHandler,
    PrivateMethodDelegator,
    PrivateMethods,
    PublicAPIDelegator,
    TradeContextResolver,
    TradeStoreOperations,
)
from .client_helpers.protocols import IOrderService, IPrivateMethods, IPublicAPI
from .dependencies_factory import (
    KalshiTradingClientDependencies,
    KalshiTradingClientDependenciesFactory,
)
from .services import OrderService

logger = logging.getLogger(__name__)


class KalshiTradingClientMixin:
    """Mixin providing lifecycle and property management for KalshiTradingClient."""

    # Declare attributes for type checking
    kalshi_client: KalshiClient
    _trade_store_manager: Any
    weather_station_resolver: WeatherStationResolver
    _orders: OrderService
    _private: PrivateMethods
    _order_polling_handler: OrderPollingOverrideHandler

    # Declare methods that subclasses must implement
    def _build_order_poller(self) -> OrderPoller:
        """Build order poller - implemented by subclass."""
        ...

    def _build_trade_finalizer(self) -> TradeFinalizer:
        """Build trade finalizer - implemented by subclass."""
        ...

    async def initialize(self) -> None:
        """Initialize the trading client and underlying connections."""
        await LifecycleManager.initialize(self.kalshi_client)

    async def close(self) -> None:
        """Close client connections and cleanup resources."""
        trade_store_manager = self._trade_store_manager
        assert trade_store_manager is not None
        await LifecycleManager.close(self.kalshi_client, trade_store_manager)

    async def __aenter__(self) -> "KalshiTradingClientMixin":
        await self.initialize()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        await self.close()
        return LifecycleManager.log_context_exit(exc_type, exc_val, exc_tb)

    @property
    def weather_station_mapping(self) -> Dict[str, Dict[str, Any]]:
        """Get weather station mapping."""
        return TradeContextResolver.get_weather_mapping(self.weather_station_resolver)

    @weather_station_mapping.setter
    def weather_station_mapping(self, mapping: Dict[str, Dict[str, Any]]) -> None:
        """Set weather station mapping."""
        TradeContextResolver.set_weather_mapping(self.weather_station_resolver, mapping)

    @property
    def icao_to_city_mapping(self) -> Dict[str, str]:
        """Get ICAO to city mapping."""
        return TradeContextResolver.create_icao_to_city_mapping(self._orders)

    async def create_order_with_polling(self, order_request: OrderRequest, timeout_seconds: int = 5) -> OrderResponse:
        """Create order with polling, respecting any overrides set on this instance."""
        return await self._order_polling_handler.create_order_with_polling(
            order_request,
            timeout_seconds,
            self.__dict__.get("create_order"),
            self.__dict__.get("cancel_order"),
            lambda: self._build_order_poller(),
            lambda: self._build_trade_finalizer(),
        )


class KalshiTradingClient(
    KalshiTradingClientMixin,
    KalshiTradingClientAPIMixin,
    KalshiTradingClientTradeStoreMixin,
    KalshiTradingClientDelegatorMixin,
):
    """Trading client for Kalshi API with Protocol-typed explicit methods.

    This class provides statically-typed access to all trading operations.
    Methods are exposed directly instead of via __getattr__ delegation,
    enabling IDE autocomplete and pyright type checking.
    """

    # Protocol-typed dependencies
    orders: IOrderService
    api: IPublicAPI
    private_methods: IPrivateMethods

    def __init__(
        self,
        kalshi_client: Optional[KalshiClient] = None,
        backoff_manager: Any = None,
        network_health_monitor: Any = None,
        trade_store: Optional[TradeStore] = None,
        telegram_handler: Any = None,
        *,
        weather_station_resolver: Optional[WeatherStationResolver] = None,
        dependencies: Optional[KalshiTradingClientDependencies] = None,
    ) -> None:
        deps = dependencies or KalshiTradingClientDependenciesFactory.create(
            kalshi_client,
            backoff_manager,
            network_health_monitor,
            trade_store,
            telegram_handler,
            weather_station_resolver,
        )

        self.kalshi_client = deps.kalshi_client
        self.backoff_manager = deps.backoff_manager
        self.trade_store = deps.trade_store
        trade_store_manager = deps.trade_store_manager
        # Ensure later trade_store overrides propagate to the manager supplier
        if trade_store_manager is not None:
            trade_store_manager.override_store_supplier(lambda: self.trade_store)
        self._trade_store_manager = trade_store_manager
        self.telegram_handler = deps.telegram_handler
        self.service_name = "kalshi_trading"
        notifier = deps.notifier
        self._notifier = notifier
        for k, v in ClientInitializer.extract_config_values(ClientInitializer.load_config()).items():
            setattr(self, k, v)
        weather_station_resolver = deps.weather_station_resolver

        assert trade_store_manager is not None
        assert notifier is not None
        assert weather_station_resolver is not None

        self.weather_station_resolver = weather_station_resolver

        (self._portfolio, self._orders, self._trade_collection) = ClientInitializer.create_services(
            self.kalshi_client,
            lambda: TradeStoreOperations.get_trade_store(trade_store_manager),
            notifier,
            weather_station_resolver,
            lambda: self._private.create_order_poller() if hasattr(self, "_private") else None,
            lambda: self._private.create_trade_finalizer() if hasattr(self, "_private") else None,
            self.telegram_handler,
        )
        self._orders.update_notifier(notifier)
        self._orders.update_telegram_handler(self.telegram_handler)
        self._private = PrivateMethods(self._orders, trade_store_manager, self.kalshi_client)
        self._delegator = PrivateMethodDelegator(self._private)
        self.is_running = False
        self._api = PublicAPIDelegator(
            self._portfolio,
            self._orders,
            self._trade_collection,
            trade_store_manager,
            self._private,
            self._orders.cancel_order,
        )
        self._order_polling_handler = OrderPollingOverrideHandler(self._orders, self._api)

        # Expose Protocol-typed interfaces
        self.orders = self._orders
        self.api = self._api
        self.private_methods = self._private

        logger.info("[KalshiTradingClient] Initialized")


__all__ = ["KalshiTradingClient"]
