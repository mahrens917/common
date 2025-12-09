"""Service creation with dependency injection."""

from ..initialization import ClientInitializer
from ..initialization_coordinator_helpers.service_provider_factory import (
    create_service_providers,
)


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
