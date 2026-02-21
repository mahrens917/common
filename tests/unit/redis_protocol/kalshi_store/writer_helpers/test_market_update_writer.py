from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.redis_protocol.kalshi_store.writer_helpers.market_update_writer import (
    MarketDataMixin,
    MarketUpdateWriter,
    RedisConnectionMixin,
    TradePriceMixin,
)
from common.redis_protocol.trade_store import TradeStoreError


@pytest.mark.asyncio
async def test_ensure_redis_uses_connection_manager_and_caches_client():
    sentinel = object()

    class DummyConnectionManager:
        async def get_redis(self):
            return sentinel

    class DummyWriter(RedisConnectionMixin):
        def __init__(self):
            self.redis = None
            self._connection_manager = DummyConnectionManager()

    writer = DummyWriter()
    redis = await writer._ensure_redis()

    assert redis is sentinel
    assert writer.redis is sentinel


@pytest.mark.asyncio
async def test_ensure_redis_raises_when_no_redis_and_no_manager():
    class DummyWriter(RedisConnectionMixin):
        def __init__(self):
            self.redis = None
            self._connection_manager = None

    writer = DummyWriter()
    with pytest.raises(RuntimeError, match="Redis connection is not initialized"):
        await writer._ensure_redis()


@pytest.mark.asyncio
async def test_write_enhanced_market_data_raises_on_empty_ticker():
    writer = MarketUpdateWriter(MagicMock(), logging.getLogger(), lambda x: x)
    with pytest.raises(TypeError, match="market_ticker must be provided"):
        await writer.write_enhanced_market_data("", "key", {"field": 1})


@pytest.mark.asyncio
async def test_write_enhanced_market_data_raises_on_empty_field_updates():
    writer = MarketUpdateWriter(MagicMock(), logging.getLogger(), lambda x: x)
    with pytest.raises(ValueError, match="field_updates must contain at least one field"):
        await writer.write_enhanced_market_data("ticker", "key", {})


@pytest.mark.asyncio
async def test_write_enhanced_market_data_reraises_redis_error():
    mock_redis = MagicMock()
    pipe = MagicMock()
    pipe.hset = MagicMock()
    pipe.execute = AsyncMock(side_effect=ConnectionError("redis down"))
    mock_redis.pipeline = MagicMock(return_value=pipe)

    writer = MarketUpdateWriter(mock_redis, logging.getLogger(), lambda x: x)
    with pytest.raises(ConnectionError):
        await writer.write_enhanced_market_data("ticker", "key", {"f": 1.0})


@pytest.mark.asyncio
async def test_update_trade_prices_returns_early_when_ask_missing():
    writer = MarketUpdateWriter(MagicMock(), logging.getLogger(), lambda x: x)
    writer._trade_store = MagicMock()
    writer._trade_store.update_trade_prices = AsyncMock()

    await writer.update_trade_prices_for_market("ticker", 50.0, None)

    writer._trade_store.update_trade_prices.assert_not_called()


@pytest.mark.asyncio
async def test_update_trade_prices_returns_early_when_bid_missing():
    writer = MarketUpdateWriter(MagicMock(), logging.getLogger(), lambda x: x)
    writer._trade_store = MagicMock()
    writer._trade_store.update_trade_prices = AsyncMock()

    await writer.update_trade_prices_for_market("ticker", None, 50.0)

    writer._trade_store.update_trade_prices.assert_not_called()


@pytest.mark.asyncio
async def test_update_trade_prices_handles_connection_error_silently():
    mock_store = MagicMock()
    mock_store.update_trade_prices = AsyncMock(side_effect=ConnectionError("lost"))

    writer = MarketUpdateWriter(MagicMock(), logging.getLogger(), lambda x: x)
    writer._trade_store = mock_store

    await writer.update_trade_prices_for_market("ticker", 10.0, 20.0)


@pytest.mark.asyncio
async def test_update_trade_prices_handles_redis_error_silently():
    from redis import RedisError

    mock_store = MagicMock()
    mock_store.update_trade_prices = AsyncMock(side_effect=RedisError("error"))

    writer = MarketUpdateWriter(MagicMock(), logging.getLogger(), lambda x: x)
    writer._trade_store = mock_store

    await writer.update_trade_prices_for_market("ticker", 10.0, 20.0)


@pytest.mark.asyncio
async def test_update_trade_prices_handles_trade_store_error_with_connection_cause():
    cause = ConnectionError("connection refused")
    exc = TradeStoreError("wrapped")
    exc.__cause__ = cause

    mock_store = MagicMock()
    mock_store.update_trade_prices = AsyncMock(side_effect=exc)

    writer = MarketUpdateWriter(MagicMock(), logging.getLogger(), lambda x: x)
    writer._trade_store = mock_store

    await writer.update_trade_prices_for_market("ticker", 10.0, 20.0)


@pytest.mark.asyncio
async def test_update_trade_prices_handles_trade_store_error_without_connection_cause():
    exc = TradeStoreError("bad data")
    exc.__cause__ = ValueError("parse failed")

    mock_store = MagicMock()
    mock_store.update_trade_prices = AsyncMock(side_effect=exc)

    writer = MarketUpdateWriter(MagicMock(), logging.getLogger(), lambda x: x)
    writer._trade_store = mock_store

    await writer.update_trade_prices_for_market("ticker", 10.0, 20.0)


@pytest.mark.asyncio
async def test_update_trade_prices_handles_value_error_silently():
    mock_store = MagicMock()
    mock_store.update_trade_prices = AsyncMock(side_effect=ValueError("bad value"))

    writer = MarketUpdateWriter(MagicMock(), logging.getLogger(), lambda x: x)
    writer._trade_store = mock_store

    await writer.update_trade_prices_for_market("ticker", 10.0, 20.0)


@pytest.mark.asyncio
async def test_get_trade_store_inner_cache_check_under_lock():
    writer = MarketUpdateWriter(None, logging.getLogger(), lambda x: x)
    sentinel = object()

    class MockLock:
        async def __aenter__(self):
            writer._trade_store = sentinel
            return self

        async def __aexit__(self, *args):
            pass

    writer._trade_store_lock = MockLock()

    result = await writer._get_trade_store()
    assert result is sentinel


@pytest.mark.asyncio
async def test_get_trade_store_raises_on_failed_initialization():
    writer = MarketUpdateWriter(None, logging.getLogger(), lambda x: x)

    mock_store = MagicMock()
    mock_store.initialize = MagicMock(return_value=False)

    with patch("common.redis_protocol.trade_store.TradeStore", return_value=mock_store):
        with pytest.raises(TradeStoreError, match="Failed to initialize TradeStore"):
            await writer._get_trade_store()
