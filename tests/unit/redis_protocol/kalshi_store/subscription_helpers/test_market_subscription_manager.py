"""Tests for Kalshi store market subscription manager."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.redis_protocol.kalshi_store.subscription_helpers import (
    market_subscription_manager,
)


class DummyRedisError(Exception):
    pass


class DummyRedisClient:
    def __init__(self, subscriptions=None):
        self.subscriptions = subscriptions or {}

    async def hgetall(self, key):
        return self.subscriptions

    async def hset(self, key, field, value):
        self.subscriptions[field] = value
        return 1

    async def hdel(self, key, field):
        self.subscriptions.pop(field, None)
        return 1


@pytest.mark.asyncio
async def test_get_subscribed_markets_filters_prefix():
    redis = DummyRedisClient(
        subscriptions={
            b"ws:KXHIGHTEST": b"1",
            b"ws:OTHER": b"0",
            "ws:OTHER2": "1",
            "other:KXHIGH": "1",
        }
    )
    manager = market_subscription_manager.MarketSubscriptionManager(lambda: AsyncMock(return_value=redis)(), "subs:key", "ws")

    markets = await manager.get_subscribed_markets()

    assert markets == {"KXHIGHTEST", "OTHER2"}


@pytest.mark.asyncio
async def test_get_subscribed_markets_logs_and_raises(monkeypatch):
    redis = MagicMock()
    redis.hgetall = AsyncMock(side_effect=DummyRedisError("boom"))
    monkeypatch.setattr(market_subscription_manager, "REDIS_ERRORS", (DummyRedisError,))
    manager = market_subscription_manager.MarketSubscriptionManager(lambda: AsyncMock(return_value=redis)(), "subs:key", "ws")

    with pytest.raises(DummyRedisError):
        await manager.get_subscribed_markets()


@pytest.mark.asyncio
async def test_add_and_remove_markets(monkeypatch):
    redis = DummyRedisClient()
    manager = market_subscription_manager.MarketSubscriptionManager(lambda: AsyncMock(return_value=redis)(), "subs:key", "ws")

    assert await manager.add_subscribed_market("KXHIGHTEST")
    assert redis.subscriptions["ws:KXHIGHTEST"] == "1"

    assert await manager.remove_subscribed_market("KXHIGHTEST")
    assert "ws:KXHIGHTEST" not in redis.subscriptions


@pytest.mark.asyncio
async def test_add_subscribed_market_handles_redis_error(monkeypatch):
    redis = MagicMock()
    redis.hset = AsyncMock(side_effect=DummyRedisError("boom"))
    monkeypatch.setattr(market_subscription_manager, "REDIS_ERRORS", (DummyRedisError,))
    manager = market_subscription_manager.MarketSubscriptionManager(lambda: AsyncMock(return_value=redis)(), "subs:key", "ws")

    with pytest.raises(DummyRedisError):
        await manager.add_subscribed_market("KXHIGHTEST")


@pytest.mark.asyncio
async def test_remove_subscribed_market_handles_redis_error(monkeypatch):
    redis = MagicMock()
    redis.hdel = AsyncMock(side_effect=DummyRedisError("boom"))
    monkeypatch.setattr(market_subscription_manager, "REDIS_ERRORS", (DummyRedisError,))
    manager = market_subscription_manager.MarketSubscriptionManager(lambda: AsyncMock(return_value=redis)(), "subs:key", "ws")

    with pytest.raises(DummyRedisError):
        await manager.remove_subscribed_market("KXHIGHTEST")


@pytest.mark.asyncio
async def test_bulk_add_empty_tickers():
    manager = market_subscription_manager.MarketSubscriptionManager(AsyncMock(), "subs:key", "ws")
    result = await manager.bulk_add_subscribed_markets([])
    assert result == 0


@pytest.mark.asyncio
async def test_bulk_add_subscribed_markets():
    pipe = MagicMock()
    pipe.hset = MagicMock()
    pipe.execute = AsyncMock(return_value=[1, 1])
    redis = MagicMock()
    redis.pipeline = MagicMock(return_value=pipe)
    manager = market_subscription_manager.MarketSubscriptionManager(AsyncMock(return_value=redis), "subs:key", "ws")

    result = await manager.bulk_add_subscribed_markets(["TICKER1", "TICKER2"])

    assert result == 2
    pipe.hset.assert_any_call("subs:key", "ws:TICKER1", "1")
    pipe.hset.assert_any_call("subs:key", "ws:TICKER2", "1")


@pytest.mark.asyncio
async def test_bulk_add_subscribed_markets_handles_redis_error(monkeypatch):
    pipe = MagicMock()
    pipe.hset = MagicMock()
    pipe.execute = AsyncMock(side_effect=DummyRedisError("boom"))
    redis = MagicMock()
    redis.pipeline = MagicMock(return_value=pipe)
    monkeypatch.setattr(market_subscription_manager, "REDIS_ERRORS", (DummyRedisError,))
    manager = market_subscription_manager.MarketSubscriptionManager(AsyncMock(return_value=redis), "subs:key", "ws")

    with pytest.raises(DummyRedisError):
        await manager.bulk_add_subscribed_markets(["TICKER1"])
