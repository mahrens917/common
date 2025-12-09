"""Component initialization helpers for InitializationCoordinator."""

import logging
from typing import Optional

from src.kalshi.api.client import KalshiClient

from ....redis_protocol.trade_store import TradeStore
from ....trading import TradeStoreManager
from ....trading.notifier_adapter import TradeNotifierAdapter
from ..initialization import ClientInitializer

logger = logging.getLogger(__name__)


def initialize_core_components(
    kalshi_client: Optional[KalshiClient],
    backoff_manager,
    network_health_monitor,
    trade_store: TradeStore,
) -> dict:
    """Initialize core clients and managers."""
    initialized_kalshi = ClientInitializer.initialize_kalshi_client(kalshi_client, trade_store)
    initialized_backoff = ClientInitializer.initialize_backoff_manager(
        backoff_manager, network_health_monitor
    )
    trade_store_manager = TradeStoreManager(
        kalshi_client=initialized_kalshi, store_supplier=lambda: trade_store
    )
    notifier = TradeNotifierAdapter()

    return {
        "kalshi_client": initialized_kalshi,
        "backoff_manager": initialized_backoff,
        "trade_store_manager": trade_store_manager,
        "notifier": notifier,
    }
