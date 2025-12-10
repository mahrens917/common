from __future__ import annotations

"""Factory methods for order pollers and trade finalizers."""


from typing import TYPE_CHECKING

from common.order_execution import OrderPoller, TradeFinalizer

if TYPE_CHECKING:
    from src.kalshi.api.client import KalshiClient

    from common.trading import TradeStoreManager


class FactoryMethods:
    """Factory methods for creating order-related components."""

    @staticmethod
    def create_order_poller(kalshi_client: KalshiClient) -> OrderPoller:
        """Create an OrderPoller instance."""
        return OrderPoller(kalshi_client.get_fills)

    @staticmethod
    def create_trade_finalizer(
        trade_store_manager: TradeStoreManager,
        context_resolver_func,
        kalshi_client: KalshiClient,
    ) -> TradeFinalizer:
        """Create a TradeFinalizer instance."""
        from src.kalshi.notifications.trade_notifier_factory import get_trade_notifier

        return TradeFinalizer(
            trade_store_provider=trade_store_manager.get_or_create,
            context_resolver=context_resolver_func,
            notifier_supplier=get_trade_notifier,
            kalshi_client=kalshi_client,
        )
