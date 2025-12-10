"""Tests for KalshiTradingClient dependency factory."""

from unittest.mock import MagicMock

import pytest

from common.kalshi_trading_client.dependencies_factory import (
    DependencyCreationConfig,
    KalshiTradingClientDependenciesFactory,
)


class _DummyClientInitializer:
    calls = []

    @staticmethod
    def initialize_kalshi_client(client, trade_store):
        _DummyClientInitializer.calls.append(("client", client, trade_store))
        return "initialized-client"

    @staticmethod
    def initialize_backoff_manager(backoff_manager, network_health_monitor):
        _DummyClientInitializer.calls.append(("backoff", backoff_manager, network_health_monitor))
        return "initialized-backoff"

    @staticmethod
    def initialize_weather_resolver(resolver):
        _DummyClientInitializer.calls.append(("weather", resolver))
        return "initialized-weather"


class _DummyTradeStoreManager:
    def __init__(self, *, kalshi_client, store_supplier):
        self.kalshi_client = kalshi_client
        self.store_supplier = store_supplier


def _patch_client_initializer(monkeypatch):
    _DummyClientInitializer.calls.clear()
    monkeypatch.setattr(
        "common.kalshi_trading_client.client_helpers.ClientInitializer",
        _DummyClientInitializer,
    )


def test_create_requires_trade_store():
    with pytest.raises(ValueError):
        KalshiTradingClientDependenciesFactory.create(trade_store=None)


def test_create_initializes_all_components(monkeypatch):
    _patch_client_initializer(monkeypatch)
    monkeypatch.setattr(
        "common.kalshi_trading_client.dependencies_factory.TradeStoreManager",
        _DummyTradeStoreManager,
    )
    notifier = MagicMock(name="notifier")
    monkeypatch.setattr(
        "common.kalshi_trading_client.dependencies_factory.TradeNotifierAdapter",
        lambda: notifier,
    )

    trade_store = MagicMock(name="store")
    deps = KalshiTradingClientDependenciesFactory.create(
        kalshi_client=MagicMock(name="client"),
        backoff_manager=MagicMock(name="backoff"),
        network_health_monitor=MagicMock(name="network"),
        trade_store=trade_store,
        telegram_handler="telegram",
        weather_station_resolver=MagicMock(name="resolver"),
    )

    assert deps.trade_store is trade_store
    assert deps.kalshi_client == "initialized-client"
    assert deps.backoff_manager == "initialized-backoff"
    assert deps.weather_station_resolver == "initialized-weather"
    assert deps.telegram_handler == "telegram"
    assert deps.notifier is notifier
    assert isinstance(deps.trade_store_manager, _DummyTradeStoreManager)


def test_create_or_use_requires_trade_store_when_all_ready(monkeypatch):
    config = DependencyCreationConfig(
        trade_store_manager=MagicMock(),
        notifier=MagicMock(),
        weather_station_resolver=MagicMock(),
    )

    with pytest.raises(ValueError):
        KalshiTradingClientDependenciesFactory.create_or_use(config)


def test_create_or_use_uses_provided_when_complete(monkeypatch):
    _patch_client_initializer(monkeypatch)
    trade_store = MagicMock(name="store")
    provided_manager = MagicMock(name="manager")
    provided_notifier = MagicMock(name="notif")
    provided_resolver = MagicMock(name="resolver")

    config = DependencyCreationConfig(
        trade_store=trade_store,
        trade_store_manager=provided_manager,
        notifier=provided_notifier,
        weather_station_resolver=provided_resolver,
        telegram_handler="telegram",
    )

    deps = KalshiTradingClientDependenciesFactory.create_or_use(config)

    assert deps.trade_store is trade_store
    assert deps.trade_store_manager is provided_manager
    assert deps.notifier is provided_notifier
    assert deps.weather_station_resolver is provided_resolver
    assert deps.telegram_handler == "telegram"
    assert deps.kalshi_client == "initialized-client"


def test_create_or_use_delegates_to_create_when_missing(monkeypatch):
    sentinel = object()
    monkeypatch.setattr(
        KalshiTradingClientDependenciesFactory,
        "create",
        staticmethod(lambda *args, **kwargs: sentinel),
    )

    config = DependencyCreationConfig(trade_store=MagicMock())
    assert KalshiTradingClientDependenciesFactory.create_or_use(config) is sentinel
