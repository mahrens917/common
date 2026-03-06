"""Consolidated helpers for InitializationCoordinator — components, results, services."""

import logging
from dataclasses import dataclass
from typing import Any, Optional

from common.kalshi_api.client import KalshiClient

from ....redis_protocol.trade_store import TradeStore
from ....trading import TradeStoreManager
from ....trading.notifier_adapter import TradeNotifierAdapter
from ..initialization import ClientInitializer
from ..trade_store_ops import TradeStoreOperations

logger = logging.getLogger(__name__)


# --- Component initialization ---


def initialize_core_components(
    kalshi_client: Optional[KalshiClient],
    backoff_manager,
    network_health_monitor,
    trade_store: TradeStore,
) -> dict:
    """Initialize core clients and managers."""
    initialized_kalshi = ClientInitializer.initialize_kalshi_client(kalshi_client, trade_store)
    initialized_backoff = ClientInitializer.initialize_backoff_manager(backoff_manager, network_health_monitor)
    trade_store_manager = TradeStoreManager(kalshi_client=initialized_kalshi, store_supplier=lambda: trade_store)
    notifier = TradeNotifierAdapter()

    return {
        "kalshi_client": initialized_kalshi,
        "backoff_manager": initialized_backoff,
        "trade_store_manager": trade_store_manager,
        "notifier": notifier,
    }


# --- Result building ---


@dataclass(frozen=True)
class ResultComponents:
    """Components for building initialization result."""

    config_vals: Any
    initialized_weather: object
    telegram_handler: object
    trade_store: TradeStore
    portfolio: object
    orders: object
    trade_collection: object
    services_holder: dict


def build_result_dict(
    core_components: dict,
    components: ResultComponents,
) -> dict:
    """Build final result dictionary with all components."""
    return {
        "kalshi_client": core_components["kalshi_client"],
        "backoff_manager": core_components["backoff_manager"],
        "trade_store": components.trade_store,
        "trade_store_manager": core_components["trade_store_manager"],
        "telegram_handler": components.telegram_handler,
        "service_name": "kalshi_trading",
        "notifier": core_components["notifier"],
        "config_vals": components.config_vals,
        "weather_station_resolver": components.initialized_weather,
        "portfolio": components.portfolio,
        "orders": components.orders,
        "trade_collection": components.trade_collection,
        "is_running": False,
        "services_holder": components.services_holder,
    }


# --- Service provider factory ---


def create_service_providers(trade_store_manager, services_holder: dict) -> dict:
    """Create service provider functions."""

    def get_trade_store():
        return TradeStoreOperations.get_trade_store(trade_store_manager)

    def get_order_poller():
        private_methods = services_holder.get("private_methods")
        return private_methods.create_order_poller() if private_methods else None

    def get_trade_finalizer():
        private_methods = services_holder.get("private_methods")
        return private_methods.create_trade_finalizer() if private_methods else None

    return {
        "get_trade_store": get_trade_store,
        "get_order_poller": get_order_poller,
        "get_trade_finalizer": get_trade_finalizer,
    }


# --- Service creation ---


def create_services(core_components, initialized_weather, telegram_handler, services_holder):
    """Create services with dependency injection."""
    trade_store_manager = core_components["trade_store_manager"]
    notifier = core_components["notifier"]
    initialized_kalshi = core_components["kalshi"]

    service_providers = create_service_providers(trade_store_manager, services_holder)
    get_trade_store = service_providers["get_trade_store"]
    get_order_poller = service_providers["get_order_poller"]
    get_trade_finalizer = service_providers["get_trade_finalizer"]

    portfolio, orders, trade_collection = ClientInitializer.create_services(
        initialized_kalshi,
        get_trade_store,
        notifier,
        initialized_weather,
        get_order_poller,
        get_trade_finalizer,
        telegram_handler,
    )

    orders.update_notifier(notifier)
    orders.update_telegram_handler(telegram_handler)

    return {"portfolio": portfolio, "orders": orders, "trade_collection": trade_collection}
