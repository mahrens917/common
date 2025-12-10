from __future__ import annotations

import logging
import sys
from datetime import timezone
from types import SimpleNamespace

import pytest
import redis.exceptions

from common.redis_protocol.trade_store.errors import TradeStoreError, TradeStoreShutdownError
from common.redis_protocol.trade_store.store_helpers.connection_manager_helpers.acquisition import (
    ConnectionAcquisitionHelper,
)
from common.redis_protocol.trade_store.store_helpers.connection_manager_helpers.retry_helpers.policy_factory import (
    create_retry_policy,
)
from common.redis_protocol.trade_store.store_helpers.connection_manager_helpers.state import (
    ConnectionStateHelper,
)
from common.redis_protocol.trade_store.store_helpers.dependency_resolver import (
    DependencyResolver,
)


@pytest.mark.asyncio
async def test_connection_acquisition_success_and_ping_retry():
    connection = SimpleNamespace(initialized=True)
    helper = ConnectionAcquisitionHelper(logging.getLogger(__name__), connection)
    redis_client = object()

    async def ensure():
        return True

    async def ping(_redis):
        return True, False

    result = await helper.get_redis(lambda: redis_client, ensure, ping)
    assert result is redis_client


@pytest.mark.asyncio
async def test_connection_acquisition_handles_missing_redis_and_ping_failure():
    connection = SimpleNamespace(initialized=False)
    helper = ConnectionAcquisitionHelper(logging.getLogger(__name__), connection)

    async def ensure():
        return False

    async def ping(_redis):
        return False, True

    with pytest.raises(TradeStoreError):
        await helper.get_redis(lambda: None, ensure, ping)

    connection.initialized = True
    with pytest.raises(TradeStoreError):

        async def ensure_ok():
            return True

        await helper.get_redis(lambda: object(), ensure_ok, ping)


def test_retry_policy_factory_clamps_values():
    policy = create_retry_policy(0, 0.0)
    assert policy.max_attempts == 1
    assert policy.initial_delay >= 0.01
    assert policy.max_delay >= 0.0


class _FakeConnection:
    def __init__(self):
        self.pool = "pool"
        self.initialized = True
        self.redis = object()
        self.reset_calls = 0
        self.closed_clients: list = []
        self.closed = False

    def reset_connection_state(self):
        self.reset_calls += 1

    async def close_redis_client(self, client):
        self.closed_clients.append(client)

    async def close(self):
        if self.closed:
            raise redis.exceptions.RedisError("boom")
        self.closed = True


@pytest.mark.asyncio
async def test_connection_state_helper_lifecycle(monkeypatch):
    helper = ConnectionStateHelper(logging.getLogger(__name__), _FakeConnection())
    helper.ensure_connection_manager()
    helper.reset_connection_state()
    assert helper._connection.reset_calls == 1

    client = object()
    await helper.close_redis_client(client, redis_setter=lambda value: None)
    assert helper._connection.closed_clients == [client]

    await helper.close(lambda value: None)
    assert helper._connection.pool is None
    assert helper._connection.initialized is False


@pytest.mark.asyncio
async def test_connection_state_helper_close_handles_errors(monkeypatch):
    failing_connection = _FakeConnection()
    failing_connection.closed = True
    helper = ConnectionStateHelper(logging.getLogger(__name__), failing_connection)
    with pytest.raises(TradeStoreShutdownError):
        await helper.close(lambda value: None)


def test_dependency_resolver_prefers_store_over_package(monkeypatch):
    store_module = SimpleNamespace(
        load_configured_timezone=lambda: "store-timezone",
        get_current_utc=lambda: "store-utc",
        get_historical_start_date=lambda: "store-start",
        get_timezone_aware_date=lambda tz: ("store-date", tz),
        get_redis_pool=lambda: "store-pool",
        Redis=type("CustomRedis", (), {})(),
        ORIGINAL_REDIS_CLASS=object(),
    )
    monkeypatch.setitem(sys.modules, "common.redis_protocol.trade_store.store", store_module)
    monkeypatch.setitem(sys.modules, "common.redis_protocol.trade_store", store_module)

    assert DependencyResolver.get_timezone_loader()() == "store-timezone"
    assert DependencyResolver.get_timestamp_provider()() == "store-utc"
    assert DependencyResolver.get_start_date_loader()() == "store-start"
    assert DependencyResolver.get_timezone_date_loader()(timezone.utc) == (
        "store-date",
        timezone.utc,
    )
    assert DependencyResolver.get_redis_pool_getter()() == "store-pool"
    assert DependencyResolver.get_redis_class() is store_module.Redis


def test_dependency_resolver_uses_builtin_when_store_missing(monkeypatch):
    import redis.asyncio as redis_asyncio

    sentinel_store = SimpleNamespace(ORIGINAL_REDIS_CLASS=redis_asyncio.Redis)
    monkeypatch.setitem(sys.modules, "common.redis_protocol.trade_store.store", sentinel_store)
    monkeypatch.setitem(sys.modules, "common.redis_protocol.trade_store", sentinel_store)

    redis_cls = DependencyResolver.get_redis_class()
    assert redis_cls.__name__ == "Redis"
