"""Tests for the Kalshi trading client component initializer helpers."""

from unittest.mock import MagicMock

from common.kalshi_trading_client.client_helpers.initialization_coordinator_helpers import (
    helpers,
)


def test_initialize_core_components(monkeypatch):
    class DummyInitializer:
        @staticmethod
        def initialize_kalshi_client(kalshi_client, trade_store):
            return kalshi_client or "kalshi-client"

        @staticmethod
        def initialize_backoff_manager(backoff_manager, network_health_monitor):
            return backoff_manager or "backoff"

    class DummyTradeStoreManager:
        def __init__(self, *, kalshi_client, store_supplier):
            self.kalshi_client = kalshi_client
            self.store_supplier = store_supplier

    class DummyNotifier:
        pass

    monkeypatch.setattr(
        helpers,
        "ClientInitializer",
        DummyInitializer,
    )
    monkeypatch.setattr(
        helpers,
        "TradeStoreManager",
        DummyTradeStoreManager,
    )
    monkeypatch.setattr(
        helpers,
        "TradeNotifierAdapter",
        DummyNotifier,
    )

    kalshi_client = MagicMock()
    backoff_manager = MagicMock()
    network_monitor = MagicMock()
    trade_store = MagicMock()

    components = helpers.initialize_core_components(kalshi_client, backoff_manager, network_monitor, trade_store)

    assert components["kalshi_client"] is kalshi_client
    assert components["backoff_manager"] is backoff_manager
    assert isinstance(components["trade_store_manager"], DummyTradeStoreManager)
    assert components["trade_store_manager"].store_supplier() is trade_store
    assert isinstance(components["notifier"], DummyNotifier)
