"""Tests for Kalshi trading client factory helpers."""

from unittest.mock import MagicMock

import pytest

from common.kalshi_trading_client.client_helpers import factory_methods
from common.kalshi_trading_client.client_helpers.factory_methods import FactoryMethods


def test_create_order_poller_delegates_get_fills(monkeypatch):
    captured = {}

    class DummyPoller:
        def __init__(self, get_fills):
            captured["get_fills"] = get_fills

    monkeypatch.setattr(
        factory_methods,
        "OrderPoller",
        DummyPoller,
    )

    client = MagicMock()
    client.get_fills = MagicMock()

    poller = FactoryMethods.create_order_poller(client)

    assert isinstance(poller, DummyPoller)
    assert captured["get_fills"] is client.get_fills


def _can_import_kalshi_notifications() -> bool:
    """Check if kalshi.notifications can be imported without errors."""
    try:
        import kalshi.notifications.trade_notifier  # noqa: F401
    except (ImportError, ModuleNotFoundError):
        return False
    else:
        return True


@pytest.mark.skipif(not _can_import_kalshi_notifications(), reason="kalshi.notifications not importable")
def test_create_trade_finalizer_wires_dependencies(monkeypatch):
    captured = {}

    class DummyTradeFinalizer:
        def __init__(
            self,
            *,
            trade_store_provider,
            context_resolver,
            notifier_supplier,
            kalshi_client,
        ):
            captured["trade_store_provider"] = trade_store_provider
            captured["context_resolver"] = context_resolver
            captured["notifier_supplier"] = notifier_supplier
            captured["kalshi_client"] = kalshi_client

    monkeypatch.setattr(
        factory_methods,
        "TradeFinalizer",
        DummyTradeFinalizer,
    )

    client = MagicMock()
    trade_store_manager = MagicMock()
    trade_store_manager.get_or_create = MagicMock()

    notifier_supplier = MagicMock()
    monkeypatch.setattr(
        "kalshi.notifications.trade_notifier.get_trade_notifier",
        lambda: notifier_supplier,
    )

    context_resolver = MagicMock()

    FactoryMethods.create_trade_finalizer(trade_store_manager, context_resolver, client)

    assert captured["trade_store_provider"] is trade_store_manager.get_or_create
    assert captured["context_resolver"] is context_resolver
    assert captured["notifier_supplier"]() == notifier_supplier
    assert captured["kalshi_client"] is client
