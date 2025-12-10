"""Unit tests for Kalshi store dependency helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

from common.redis_protocol.kalshi_store import attribute_resolver as attribute_resolver_module
from common.redis_protocol.kalshi_store import dependencies_factory_helpers as helpers
from common.redis_protocol.kalshi_store.dependencies_factory_helpers import (
    create_attribute_resolver,
    create_core_components,
    create_delegators,
)


class DummyConnectionManager:
    def __init__(self, logger: MagicMock, redis: MagicMock | None) -> None:
        self.logger = logger
        self.redis = redis or MagicMock(name="connection_redis")


class DummyMetadataAdapter:
    def __init__(self, logger: MagicMock, weather_resolver: MagicMock) -> None:
        self.logger = logger
        self.weather_resolver = weather_resolver


class DummySubscriptionTracker:
    SUBSCRIPTIONS_KEY = "subs-key"

    def __init__(self, connection: DummyConnectionManager, logger: MagicMock, prefix: str) -> None:
        self.connection = connection
        self.logger = logger
        self.prefix = prefix


class DummyMarketReader:
    def __init__(self, connection, logger, metadata, service_prefix, subscriptions_key):
        self.connection = connection
        self.logger = logger
        self.metadata = metadata
        self.service_prefix = service_prefix
        self.subscriptions_key = subscriptions_key

    def get_market_key(self) -> str:
        return "market-key"


class DummyWriterDependenciesFactory:
    @staticmethod
    def create(redis, logger, metadata, connection):
        return {
            "redis": redis,
            "logger": logger,
            "metadata": metadata,
            "connection": connection,
        }


class DummyMarketWriter:
    def __init__(self, redis, logger, connection, metadata, dependencies=None, **kwargs):
        self.redis = redis
        self.logger = logger
        self.connection = connection
        self.metadata = metadata
        self.writer_dependencies = dependencies or kwargs.get("writer_dependencies")


class DummyMarketCleaner:
    def __init__(self, **kwargs):
        self.attributes = kwargs


class DummyOrderbookProcessor:
    def __init__(self, **kwargs):
        self.attributes = kwargs


class DummyDelegator:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class DummyAttributeResolver:
    def __init__(self, config):
        self.config = config


class DummyAttributeResolverDelegators:
    def __init__(self, **delegators):
        self.delegators = delegators


def _patch_dependencies(monkeypatch):
    monkeypatch.setattr(helpers, "RedisConnectionManager", DummyConnectionManager)
    monkeypatch.setattr(helpers, "KalshiMetadataAdapter", DummyMetadataAdapter)
    monkeypatch.setattr(helpers, "KalshiSubscriptionTracker", DummySubscriptionTracker)
    monkeypatch.setattr(helpers, "KalshiMarketReader", DummyMarketReader)
    monkeypatch.setattr(
        helpers,
        "KalshiMarketWriterDependenciesFactory",
        DummyWriterDependenciesFactory,
    )
    monkeypatch.setattr(helpers, "KalshiMarketWriter", DummyMarketWriter)
    monkeypatch.setattr(helpers, "KalshiMarketCleaner", DummyMarketCleaner)
    monkeypatch.setattr(helpers, "KalshiOrderbookProcessor", DummyOrderbookProcessor)
    monkeypatch.setattr(helpers, "PropertyManager", DummyDelegator)
    monkeypatch.setattr(helpers, "ConnectionDelegator", DummyDelegator)
    monkeypatch.setattr(helpers, "MetadataDelegator", DummyDelegator)
    monkeypatch.setattr(helpers, "SubscriptionDelegator", DummyDelegator)
    monkeypatch.setattr(helpers, "MarketQueryDelegator", DummyDelegator)
    monkeypatch.setattr(helpers, "WriteDelegator", DummyDelegator)
    monkeypatch.setattr(helpers, "OrderbookDelegator", DummyDelegator)
    monkeypatch.setattr(helpers, "CleanupDelegator", DummyDelegator)
    monkeypatch.setattr(helpers, "UtilityDelegator", DummyDelegator)
    monkeypatch.setattr(helpers, "StorageDelegator", DummyDelegator)
    monkeypatch.setattr(helpers, "AttributeResolver", DummyAttributeResolver)

    monkeypatch.setattr(
        attribute_resolver_module,
        "AttributeResolverDelegators",
        DummyAttributeResolverDelegators,
    )


def _build_core(monkeypatch):
    _patch_dependencies(monkeypatch)
    logger = MagicMock(name="logger")
    redis_client = MagicMock(name="redis")
    metadata_resolver = MagicMock(name="weather_resolver")

    components = create_core_components(
        logger,
        redis_client,
        service_prefix="prefix",
        weather_resolver=metadata_resolver,
        update_trade_prices_callback=lambda *_: None,
    )

    return components


def test_create_core_components_returns_expected_objects(monkeypatch):
    components = _build_core(monkeypatch)

    assert isinstance(components["connection"], DummyConnectionManager)
    assert components["writer"].redis is components["connection"].redis
    assert components["writer"].writer_dependencies["redis"] is components["writer"].redis
    assert isinstance(components["reader"], DummyMarketReader)
    assert components["subscription"].SUBSCRIPTIONS_KEY == "subs-key"


def test_create_delegators_wires_components(monkeypatch):
    components = _build_core(monkeypatch)
    delegators = create_delegators(components, MagicMock(name="resolver"))

    assert isinstance(delegators["conn_delegator"], DummyDelegator)
    assert delegators["conn_delegator"].args[0] is components["connection"]
    assert isinstance(delegators["write_delegator"], DummyDelegator)
    assert delegators["write_delegator"].args[0] is components["writer"]
    for key in (
        "property_mgr",
        "metadata_delegator",
        "subscription_delegator",
        "query_delegator",
        "write_delegator",
        "orderbook_delegator",
        "cleanup_delegator",
        "utility_delegator",
        "storage_delegator",
    ):
        assert key in delegators


def test_create_attribute_resolver_uses_delegators(monkeypatch):
    dummy = object()
    delegators = {
        "storage_delegator": dummy,
        "write_delegator": dummy,
        "utility_delegator": dummy,
        "conn_delegator": dummy,
        "metadata_delegator": dummy,
        "subscription_delegator": dummy,
        "query_delegator": dummy,
        "orderbook_delegator": dummy,
        "cleanup_delegator": dummy,
    }

    _patch_dependencies(monkeypatch)
    resolver = create_attribute_resolver(delegators)

    assert isinstance(resolver, DummyAttributeResolver)
    assert isinstance(resolver.config, DummyAttributeResolverDelegators)
    assert resolver.config.delegators["storage_delegator"] is dummy
