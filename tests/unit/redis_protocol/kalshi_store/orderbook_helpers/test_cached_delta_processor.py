"""Tests for DeltaProcessor cached path."""

from unittest.mock import AsyncMock

import pytest

from common.redis_protocol.kalshi_store.orderbook_helpers.delta_processor import DeltaProcessor
from common.redis_protocol.kalshi_store.orderbook_helpers.orderbook_cache import OrderbookCache


@pytest.fixture
def cache() -> OrderbookCache:
    return OrderbookCache()


@pytest.fixture
def processor(cache: OrderbookCache) -> DeltaProcessor:
    callback = AsyncMock()
    proc = DeltaProcessor(callback)
    proc.set_cache(cache)
    return proc


class TestProcessDeltaCached:
    @pytest.mark.asyncio
    async def test_yes_bid_delta_updates_cache(self, processor: DeltaProcessor, cache: OrderbookCache) -> None:
        cache.store_snapshot("market:key", {"yes_bids": {}, "timestamp": "0"})
        redis_mock = AsyncMock()
        result = await processor.process_orderbook_delta(
            redis=redis_mock,
            market_key="market:key",
            market_ticker="TICKER",
            msg_data={"side": "yes", "price": 50, "delta": 10},
            timestamp="100",
        )
        assert result is True
        redis_mock.hset.assert_called_once()
        snapshot = cache.get_snapshot("market:key")
        assert snapshot is not None
        assert snapshot["timestamp"] == "100"

    @pytest.mark.asyncio
    async def test_no_side_delta_updates_asks(self, processor: DeltaProcessor, cache: OrderbookCache) -> None:
        cache.store_snapshot("market:key", {"yes_asks": {}, "timestamp": "0"})
        redis_mock = AsyncMock()
        result = await processor.process_orderbook_delta(
            redis=redis_mock,
            market_key="market:key",
            market_ticker="TICKER",
            msg_data={"side": "no", "price": 40, "delta": 5},
            timestamp="200",
        )
        assert result is True
        snapshot = cache.get_snapshot("market:key")
        assert snapshot is not None
        assert "yes_asks" in snapshot

    @pytest.mark.asyncio
    async def test_invalid_side_returns_false(self, processor: DeltaProcessor) -> None:
        redis_mock = AsyncMock()
        result = await processor.process_orderbook_delta(
            redis=redis_mock,
            market_key="market:key",
            market_ticker="TICKER",
            msg_data={"side": "unknown", "price": 50, "delta": 10},
            timestamp="100",
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_trade_price_callback_called(self, processor: DeltaProcessor, cache: OrderbookCache) -> None:
        cache.store_snapshot("market:key", {"yes_bids": {}, "yes_bid": "50", "yes_ask": "60", "timestamp": "0"})
        redis_mock = AsyncMock()
        await processor.process_orderbook_delta(
            redis=redis_mock,
            market_key="market:key",
            market_ticker="TICKER",
            msg_data={"side": "yes", "price": 50, "delta": 10},
            timestamp="100",
        )
        callback = processor.get_update_callback()
        callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_cold_start_empty_cache(self, processor: DeltaProcessor, cache: OrderbookCache) -> None:
        """Delta on a market not yet in cache should still work (empty side data)."""
        redis_mock = AsyncMock()
        result = await processor.process_orderbook_delta(
            redis=redis_mock, market_key="new:key", market_ticker="NEW", msg_data={"side": "yes", "price": 50, "delta": 10}, timestamp="300"
        )
        assert result is True
        redis_mock.hset.assert_called_once()

    @pytest.mark.asyncio
    async def test_price_change_triggers_stream_publish(self, processor: DeltaProcessor, cache: OrderbookCache) -> None:
        """When best price changes, event stream should be published."""
        cache.store_snapshot("market:key", {"yes_bids": {}, "yes_bid": "50", "timestamp": "0"})
        # Seed previous best
        cache.check_price_changed("market:key")

        redis_mock = AsyncMock()
        redis_mock.hget = AsyncMock(return_value="EVENT-TICKER")
        redis_mock.xadd = AsyncMock()
        await processor.process_orderbook_delta(
            redis=redis_mock,
            market_key="market:key",
            market_ticker="TICKER",
            msg_data={"side": "yes", "price": 55, "delta": 10},
            timestamp="200",
        )
        # New bid price should trigger stream publish
        redis_mock.xadd.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_price_change_skips_stream(self, processor: DeltaProcessor, cache: OrderbookCache) -> None:
        """When best price doesn't change, stream should not be published."""
        cache.store_snapshot("market:key", {"yes_bids": {"50.0": 10}, "yes_bid": "50.0", "timestamp": "0"})
        cache.check_price_changed("market:key")

        redis_mock = AsyncMock()
        redis_mock.xadd = AsyncMock()
        # Delta changes size at same price — no price change
        await processor.process_orderbook_delta(
            redis=redis_mock,
            market_key="market:key",
            market_ticker="TICKER",
            msg_data={"side": "yes", "price": 50, "delta": 5},
            timestamp="200",
        )
        redis_mock.xadd.assert_not_called()
