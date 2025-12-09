from __future__ import annotations

import pytest
import redis.exceptions

from src.common.redis_protocol.subscription_store_helpers.channel_resolver import ChannelResolver
from src.common.redis_protocol.subscription_store_helpers.connection_manager import (
    SubscriptionStoreConnectionManager,
)
from src.common.redis_protocol.subscription_store_helpers.retrieval import SubscriptionRetrieval


class _FakePubSub:
    def __init__(self):
        self.closed = False

    async def aclose(self):
        self.closed = True


class _FakeRedis:
    def __init__(self):
        self.closed = False
        self.pubsub_instance = _FakePubSub()

    def pubsub(self):
        return self.pubsub_instance

    async def aclose(self):
        self.closed = True


@pytest.mark.asyncio
async def test_subscription_connection_manager_initialize_and_cleanup(monkeypatch):
    fake_pool = object()
    fake_redis = _FakeRedis()
    monkeypatch.setattr(
        "src.common.redis_protocol.subscription_store_helpers.connection_manager.Redis",
        lambda *args, **kwargs: fake_redis,
    )

    manager = SubscriptionStoreConnectionManager(pool=fake_pool)
    await manager.initialize()

    assert manager.redis is fake_redis
    assert manager.pubsub is fake_redis.pubsub_instance
    assert manager._initialized is True
    assert await manager.get_redis() is fake_redis

    await manager.cleanup()
    assert manager.redis is None
    assert manager._initialized is False
    assert fake_redis.closed is True
    assert fake_redis.pubsub_instance.closed is True


@pytest.mark.asyncio
async def test_subscription_connection_manager_fetches_pool(monkeypatch):
    fake_pool = object()
    fake_redis = _FakeRedis()

    async def _get_pool():
        return fake_pool

    monkeypatch.setattr(
        "src.common.redis_protocol.subscription_store_helpers.connection_manager.Redis",
        lambda *args, **kwargs: fake_redis,
    )
    import src.common.redis_protocol.connection as connection_module

    monkeypatch.setattr(connection_module, "get_redis_pool", _get_pool)

    manager = SubscriptionStoreConnectionManager(pool=None)
    await manager.initialize()
    assert manager.redis is fake_redis


@pytest.mark.asyncio
async def test_subscription_connection_manager_requires_initialization():
    manager = SubscriptionStoreConnectionManager()
    with pytest.raises(RuntimeError):
        await manager.get_redis()


def test_channel_resolver_routes_channels():
    resolver = ChannelResolver("kalshi")
    assert resolver.get_subscription_channel() == "kalshi:subscription:updates"
    assert resolver.get_subscription_hash() == "kalshi:subscriptions"

    deribit_resolver = ChannelResolver("deribit")
    assert deribit_resolver.get_subscription_channel() == "deribit:subscription:updates"
    assert deribit_resolver.get_subscription_hash() == "deribit:subscriptions"

    with pytest.raises(TypeError):
        ChannelResolver("unknown")


class _MappingRedis:
    def __init__(self, mapping):
        self.mapping = mapping
        self.calls = 0

    async def hgetall(self, key):
        self.calls += 1
        if isinstance(self.mapping, Exception):
            raise self.mapping
        return self.mapping


@pytest.mark.asyncio
async def test_subscription_retrieval_groups_and_verifies(monkeypatch):
    retrieval = SubscriptionRetrieval()
    redis_client = _MappingRedis(
        {
            b"instrument:BTC": b"chan-1",
            "price_index:ETH": "chan-2",
            "volatility_index:SOL": "chan-3",
            "unknown": "skip-me",
        }
    )

    grouped = await retrieval.get_active_subscriptions(redis_client, "hash-key")
    assert grouped["instruments"] == {"BTC": "chan-1"}
    assert grouped["price_indices"] == {"ETH": "chan-2"}
    assert grouped["volatility_indices"] == {"SOL": "chan-3"}

    counts = await retrieval.verify_subscriptions(redis_client, "hash-key")
    assert counts == {"instruments": 1, "price_indices": 1, "volatility_indices": 1}


@pytest.mark.asyncio
async def test_subscription_retrieval_handles_errors():
    retrieval = SubscriptionRetrieval()
    redis_client = _MappingRedis(redis.exceptions.RedisError("fail"))

    assert await retrieval.get_active_subscriptions(redis_client, "hash") == {}
    assert await retrieval.verify_subscriptions(redis_client, "hash") == {
        "instruments": 0,
        "price_indices": 0,
        "volatility_indices": 0,
    }
