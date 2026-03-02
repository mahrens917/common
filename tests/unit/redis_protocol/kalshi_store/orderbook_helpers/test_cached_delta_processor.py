"""Tests for DeltaProcessor cached path."""

from unittest.mock import AsyncMock

import pytest

from common.redis_protocol.coalescing_batcher import CoalescingBatcher
from common.redis_protocol.kalshi_store.orderbook_helpers.delta_processor import DeltaProcessor
from common.redis_protocol.kalshi_store.orderbook_helpers.orderbook_cache import OrderbookCache


@pytest.fixture
def cache() -> OrderbookCache:
    return OrderbookCache()


@pytest.fixture
def batcher() -> CoalescingBatcher:
    async def noop(batch: list) -> None:
        pass

    return CoalescingBatcher(noop, "test")


@pytest.fixture
def processor(cache: OrderbookCache, batcher: CoalescingBatcher) -> DeltaProcessor:
    callback = AsyncMock()
    proc = DeltaProcessor(callback)
    proc.set_cache_and_batcher(cache, batcher)
    return proc


class TestProcessDeltaCached:
    @pytest.mark.asyncio
    async def test_yes_bid_delta_updates_cache(self, processor: DeltaProcessor, cache: OrderbookCache, batcher: CoalescingBatcher) -> None:
        cache.store_snapshot("market:key", {"yes_bids": "{}", "timestamp": "0"})
        redis_mock = AsyncMock()
        result = await processor.process_orderbook_delta(
            redis=redis_mock,
            market_key="market:key",
            market_ticker="TICKER",
            msg_data={"side": "yes", "price": 50, "delta": 10},
            timestamp="100",
        )
        assert result is True
        assert "market:key" in batcher._pending
        update = batcher._pending["market:key"]
        assert update.market_key == "market:key"
        assert update.market_ticker == "TICKER"
        assert update.timestamp == "100"

    @pytest.mark.asyncio
    async def test_no_side_delta_updates_asks(self, processor: DeltaProcessor, cache: OrderbookCache, batcher: CoalescingBatcher) -> None:
        cache.store_snapshot("market:key", {"yes_asks": "{}", "timestamp": "0"})
        redis_mock = AsyncMock()
        result = await processor.process_orderbook_delta(
            redis=redis_mock,
            market_key="market:key",
            market_ticker="TICKER",
            msg_data={"side": "no", "price": 40, "delta": 5},
            timestamp="200",
        )
        assert result is True
        update = batcher._pending["market:key"]
        assert "yes_asks" in update.fields

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
        cache.store_snapshot("market:key", {"yes_bids": "{}", "yes_bid": "50", "yes_ask": "60", "timestamp": "0"})
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
    async def test_cold_start_empty_cache(self, processor: DeltaProcessor, batcher: CoalescingBatcher) -> None:
        """Delta on a market not yet in cache should still work (empty side data)."""
        redis_mock = AsyncMock()
        result = await processor.process_orderbook_delta(
            redis=redis_mock, market_key="new:key", market_ticker="NEW", msg_data={"side": "yes", "price": 50, "delta": 10}, timestamp="300"
        )
        assert result is True
        assert "new:key" in batcher._pending
