"""Build final initialization result dictionary."""

from dataclasses import dataclass
from typing import Any

from ....redis_protocol.trade_store import TradeStore


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
