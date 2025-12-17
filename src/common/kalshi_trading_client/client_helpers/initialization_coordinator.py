"""Coordinate initialization of all trading client components."""

import logging
from dataclasses import dataclass
from typing import Any, Optional

from common.kalshi_api.client import KalshiClient

from ...redis_protocol.trade_store import TradeStore
from ...trading import TradeStoreManager, WeatherStationResolver
from ...trading.notifier_adapter import TradeNotifierAdapter
from .initialization import ClientInitializer
from .initialization_coordinator_helpers.service_provider_factory import (
    create_service_providers,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _InitializationResultComponents:
    """Components needed to build initialization result."""

    initialized_kalshi: KalshiClient
    initialized_backoff: object
    trade_store: TradeStore
    trade_store_manager: TradeStoreManager
    telegram_handler: object
    notifier: TradeNotifierAdapter
    config_vals: Any
    initialized_weather: WeatherStationResolver
    portfolio: object
    orders: object
    trade_collection: object
    services_holder: dict


class InitializationCoordinator:
    """
    Coordinate all initialization steps for trading client.

    Centralizes the complex initialization sequence including:
    - Client/manager setup
    - Service creation
    - Configuration loading
    - Component wiring
    """

    @staticmethod
    def initialize_all_components(
        kalshi_client: Optional[KalshiClient],
        backoff_manager,
        network_health_monitor,
        trade_store: TradeStore,
        telegram_handler,
        weather_station_resolver: Optional[WeatherStationResolver],
    ) -> dict:
        """
        Initialize all trading client components in correct order.

        Returns:
            Dictionary with all initialized components and configuration
        """
        (
            initialized_kalshi,
            initialized_backoff,
            trade_store_manager,
            notifier,
        ) = _initialize_core_clients(kalshi_client, trade_store, backoff_manager, network_health_monitor)

        config_vals = ClientInitializer.extract_config_values(ClientInitializer.load_config())
        initialized_weather = ClientInitializer.initialize_weather_resolver(weather_station_resolver)
        services_holder = {}
        portfolio, orders, trade_collection = _create_service_stack(
            initialized_kalshi,
            trade_store_manager,
            notifier,
            initialized_weather,
            services_holder,
            telegram_handler,
        )
        _wire_order_dependencies(orders, notifier, telegram_handler)

        logger.info("[InitializationCoordinator] Initialized unified trading client with trade collection")

        components = _InitializationResultComponents(
            initialized_kalshi=initialized_kalshi,
            initialized_backoff=initialized_backoff,
            trade_store=trade_store,
            trade_store_manager=trade_store_manager,
            telegram_handler=telegram_handler,
            notifier=notifier,
            config_vals=config_vals,
            initialized_weather=initialized_weather,
            portfolio=portfolio,
            orders=orders,
            trade_collection=trade_collection,
            services_holder=services_holder,
        )
        return _build_initialization_result(components)


def _initialize_core_clients(
    kalshi_client: Optional[KalshiClient],
    trade_store: TradeStore,
    backoff_manager,
    network_health_monitor,
):
    initialized_kalshi = ClientInitializer.initialize_kalshi_client(kalshi_client, trade_store)
    initialized_backoff = ClientInitializer.initialize_backoff_manager(backoff_manager, network_health_monitor)
    trade_store_manager = TradeStoreManager(kalshi_client=initialized_kalshi, store_supplier=lambda: trade_store)
    notifier = TradeNotifierAdapter()
    return initialized_kalshi, initialized_backoff, trade_store_manager, notifier


def _create_service_stack(
    initialized_kalshi,
    trade_store_manager,
    notifier,
    initialized_weather,
    services_holder,
    telegram_handler,
):
    service_providers = create_service_providers(trade_store_manager, services_holder)
    get_trade_store = service_providers["get_trade_store"]
    get_order_poller = service_providers["get_order_poller"]
    get_trade_finalizer = service_providers["get_trade_finalizer"]

    return ClientInitializer.create_services(
        initialized_kalshi,
        get_trade_store,
        notifier,
        initialized_weather,
        get_order_poller,
        get_trade_finalizer,
        telegram_handler,
    )


def _wire_order_dependencies(orders, notifier, telegram_handler) -> None:
    orders.update_notifier(notifier)
    orders.update_telegram_handler(telegram_handler)


def _build_initialization_result(components: _InitializationResultComponents) -> dict:
    """Build initialization result dictionary from components."""
    return {
        "kalshi_client": components.initialized_kalshi,
        "backoff_manager": components.initialized_backoff,
        "trade_store": components.trade_store,
        "trade_store_manager": components.trade_store_manager,
        "telegram_handler": components.telegram_handler,
        "service_name": "kalshi_trading",
        "notifier": components.notifier,
        "config_vals": components.config_vals,
        "weather_station_resolver": components.initialized_weather,
        "portfolio": components.portfolio,
        "orders": components.orders,
        "trade_collection": components.trade_collection,
        "is_running": False,
        "services_holder": components.services_holder,
    }
