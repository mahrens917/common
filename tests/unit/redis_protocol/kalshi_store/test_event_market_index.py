"""Tests for EventMarketIndex."""

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from common.redis_protocol.kalshi_store.event_market_index import EventMarketIndex


def _make_market(event_ticker: str, market_ticker: str) -> dict:
    return {
        "event_ticker": event_ticker,
        "market_ticker": market_ticker,
        "yes_bid": "50",
        "yes_ask": "55",
    }


class TestEventMarketIndex:
    """Tests for EventMarketIndex initialization and lookups."""

    @pytest.mark.asyncio
    async def test_initialize_builds_index(self):
        markets = [
            _make_market("EVT-A", "MKT-A1"),
            _make_market("EVT-A", "MKT-A2"),
            _make_market("EVT-B", "MKT-B1"),
        ]
        store = MagicMock()
        store.get_all_markets = AsyncMock(return_value=markets)

        index = EventMarketIndex()
        await index.initialize(store)

        assert index.event_count == 2
        assert index.market_count == 3

    @pytest.mark.asyncio
    async def test_get_event_markets(self):
        markets = [
            _make_market("EVT-A", "MKT-A1"),
            _make_market("EVT-A", "MKT-A2"),
        ]
        store = MagicMock()
        store.get_all_markets = AsyncMock(return_value=markets)

        index = EventMarketIndex()
        await index.initialize(store)

        result = index.get_event_markets("EVT-A")
        assert len(result) == 2
        tickers = {m["market_ticker"] for m in result}
        assert tickers == {"MKT-A1", "MKT-A2"}

    @pytest.mark.asyncio
    async def test_get_event_markets_unknown_event(self):
        store = MagicMock()
        store.get_all_markets = AsyncMock(return_value=[])

        index = EventMarketIndex()
        await index.initialize(store)

        assert index.get_event_markets("UNKNOWN") == []

    @pytest.mark.asyncio
    async def test_get_event_market_tickers(self):
        markets = [_make_market("EVT-A", "MKT-A1"), _make_market("EVT-A", "MKT-A2")]
        store = MagicMock()
        store.get_all_markets = AsyncMock(return_value=markets)

        index = EventMarketIndex()
        await index.initialize(store)

        assert index.get_event_market_tickers("EVT-A") == {"MKT-A1", "MKT-A2"}

    @pytest.mark.asyncio
    async def test_refresh_market_updates_cache(self):
        store = MagicMock()
        store.get_all_markets = AsyncMock(return_value=[_make_market("EVT-A", "MKT-A1")])

        index = EventMarketIndex()
        await index.initialize(store)

        redis = MagicMock()
        redis.hgetall = AsyncMock(return_value={b"yes_bid": b"60", b"yes_ask": b"65"})

        result = await index.refresh_market(redis, "MKT-A1")

        assert result is not None
        assert result["yes_bid"] == "60"
        assert result["yes_ask"] == "65"
        assert result["market_ticker"] == "MKT-A1"

        cached = index.get_event_markets("EVT-A")
        assert cached[0]["yes_bid"] == "60"

    @pytest.mark.asyncio
    async def test_refresh_market_returns_none_if_missing(self):
        store = MagicMock()
        store.get_all_markets = AsyncMock(return_value=[])

        index = EventMarketIndex()
        await index.initialize(store)

        redis = MagicMock()
        redis.hgetall = AsyncMock(return_value={})

        result = await index.refresh_market(redis, "GONE")
        assert result is None

    def test_update_index_registers_new_market(self):
        index = EventMarketIndex()
        index.update_index("EVT-NEW", "MKT-NEW")

        assert "MKT-NEW" in index.get_event_market_tickers("EVT-NEW")

    @pytest.mark.asyncio
    async def test_skips_markets_without_tickers(self):
        markets = [{"event_ticker": "EVT-A"}, {"market_ticker": "MKT-B"}]
        store = MagicMock()
        store.get_all_markets = AsyncMock(return_value=markets)

        index = EventMarketIndex()
        await index.initialize(store)

        assert index.event_count == 0
        assert index.market_count == 0


class TestApplyStreamUpdate:
    """Tests for EventMarketIndex.apply_stream_update."""

    @pytest.mark.asyncio
    async def test_cache_hit_merges_fields(self):
        store = MagicMock()
        store.get_all_markets = AsyncMock(return_value=[_make_market("EVT-A", "MKT-A1")])

        index = EventMarketIndex()
        await index.initialize(store)

        result = index.apply_stream_update("MKT-A1", {"yes_bid": "70", "yes_ask": "75"})

        assert result is not None
        assert result["yes_bid"] == "70"
        assert result["yes_ask"] == "75"
        assert result["event_ticker"] == "EVT-A"

    @pytest.mark.asyncio
    async def test_cache_hit_preserves_existing_fields(self):
        store = MagicMock()
        store.get_all_markets = AsyncMock(return_value=[_make_market("EVT-A", "MKT-A1")])

        index = EventMarketIndex()
        await index.initialize(store)

        result = index.apply_stream_update("MKT-A1", {"yes_bid": "70"})

        assert result is not None
        assert result["yes_bid"] == "70"
        assert result["yes_ask"] == "55"

    def test_cache_miss_with_event_ticker_creates_entry(self):
        index = EventMarketIndex()

        result = index.apply_stream_update("MKT-NEW", {"event_ticker": "EVT-NEW", "yes_bid": "40"})

        assert result is not None
        assert result["market_ticker"] == "MKT-NEW"
        assert result["yes_bid"] == "40"
        assert index.market_count == 1
        assert "MKT-NEW" in index.get_event_market_tickers("EVT-NEW")

    def test_cache_miss_without_event_ticker_returns_none(self):
        index = EventMarketIndex()

        result = index.apply_stream_update("MKT-UNKNOWN", {"yes_bid": "40"})

        assert result is None
        assert index.market_count == 0

    @pytest.mark.asyncio
    async def test_updates_visible_through_get_event_markets(self):
        store = MagicMock()
        store.get_all_markets = AsyncMock(return_value=[_make_market("EVT-A", "MKT-A1")])

        index = EventMarketIndex()
        await index.initialize(store)

        index.apply_stream_update("MKT-A1", {"yes_bid": "99"})

        markets = index.get_event_markets("EVT-A")
        assert markets[0]["yes_bid"] == "99"


def _mock_redis_scan(key_count: int) -> MagicMock:
    """Build a mock redis that returns key_count plain market keys from SCAN."""
    redis = MagicMock()
    keys = [f"markets:kalshi:MKT-{i}" for i in range(key_count)]

    async def mock_scan(cursor=0, match="", count=500):
        return 0, keys

    redis.scan = AsyncMock(side_effect=mock_scan)
    return redis


class TestReconcile:
    """Tests for EventMarketIndex.reconcile."""

    @pytest.mark.asyncio
    async def test_matching_count_returns_false(self):
        markets = [_make_market("EVT-A", f"MKT-{i}") for i in range(10)]
        store = MagicMock()
        store.get_all_markets = AsyncMock(return_value=markets)

        index = EventMarketIndex()
        await index.initialize(store)

        redis = _mock_redis_scan(10)
        assert await index.reconcile(redis) is False

    @pytest.mark.asyncio
    async def test_within_tolerance_returns_false(self):
        markets = [_make_market("EVT-A", f"MKT-{i}") for i in range(10)]
        store = MagicMock()
        store.get_all_markets = AsyncMock(return_value=markets)

        index = EventMarketIndex()
        await index.initialize(store)

        redis = _mock_redis_scan(14)
        assert await index.reconcile(redis) is False

    @pytest.mark.asyncio
    async def test_diverged_count_returns_true(self, caplog):
        markets = [_make_market("EVT-A", f"MKT-{i}") for i in range(10)]
        store = MagicMock()
        store.get_all_markets = AsyncMock(return_value=markets)

        index = EventMarketIndex()
        await index.initialize(store)

        redis = _mock_redis_scan(20)
        with caplog.at_level(logging.WARNING):
            result = await index.reconcile(redis)

        assert result is True
        assert "count divergence" in caplog.text

    @pytest.mark.asyncio
    async def test_excludes_subkeys(self):
        """SCAN keys with :trading_signal or :position_state are excluded."""
        markets = [_make_market("EVT-A", f"MKT-{i}") for i in range(5)]
        store = MagicMock()
        store.get_all_markets = AsyncMock(return_value=markets)

        index = EventMarketIndex()
        await index.initialize(store)

        redis = MagicMock()
        keys = [
            "markets:kalshi:MKT-0",
            "markets:kalshi:MKT-1",
            "markets:kalshi:MKT-2",
            "markets:kalshi:MKT-3",
            "markets:kalshi:MKT-4",
            "markets:kalshi:MKT-0:trading_signal",
            "markets:kalshi:MKT-1:position_state",
        ]

        async def mock_scan(cursor=0, match="", count=500):
            return 0, keys

        redis.scan = AsyncMock(side_effect=mock_scan)
        assert await index.reconcile(redis) is False


class TestApplyStreamUpdateSettled:
    """Tests for settled/closed status eviction in apply_stream_update."""

    @pytest.mark.asyncio
    async def test_settled_status_evicts_market(self):
        store = MagicMock()
        store.get_all_markets = AsyncMock(return_value=[_make_market("EVT-A", "MKT-A1")])

        index = EventMarketIndex()
        await index.initialize(store)

        result = index.apply_stream_update("MKT-A1", {"status": "settled"})

        assert result is None
        assert index.market_count == 0

    @pytest.mark.asyncio
    async def test_closed_status_evicts_market(self):
        store = MagicMock()
        store.get_all_markets = AsyncMock(return_value=[_make_market("EVT-A", "MKT-A1")])

        index = EventMarketIndex()
        await index.initialize(store)

        result = index.apply_stream_update("MKT-A1", {"status": "closed"})

        assert result is None
        assert index.market_count == 0

    @pytest.mark.asyncio
    async def test_bytes_settled_status_evicts_market(self):
        store = MagicMock()
        store.get_all_markets = AsyncMock(return_value=[_make_market("EVT-A", "MKT-A1")])

        index = EventMarketIndex()
        await index.initialize(store)

        result = index.apply_stream_update("MKT-A1", {"status": b"settled"})

        assert result is None
        assert index.market_count == 0

    @pytest.mark.asyncio
    async def test_evict_removes_event_index_entry(self):
        store = MagicMock()
        store.get_all_markets = AsyncMock(return_value=[_make_market("EVT-A", "MKT-A1")])

        index = EventMarketIndex()
        await index.initialize(store)

        index.apply_stream_update("MKT-A1", {"status": "settled"})

        assert "MKT-A1" not in index.get_event_market_tickers("EVT-A")
        assert index.event_count == 1  # event key still exists, but set is empty


class TestGetAllHelpers:
    """Tests for get_all_tickers and get_all_markets."""

    @pytest.mark.asyncio
    async def test_get_all_tickers(self):
        markets = [
            _make_market("EVT-A", "MKT-A1"),
            _make_market("EVT-A", "MKT-A2"),
        ]
        store = MagicMock()
        store.get_all_markets = AsyncMock(return_value=markets)

        index = EventMarketIndex()
        await index.initialize(store)

        tickers = index.get_all_tickers()
        assert set(tickers) == {"MKT-A1", "MKT-A2"}

    @pytest.mark.asyncio
    async def test_get_all_markets(self):
        markets = [
            _make_market("EVT-A", "MKT-A1"),
            _make_market("EVT-B", "MKT-B1"),
        ]
        store = MagicMock()
        store.get_all_markets = AsyncMock(return_value=markets)

        index = EventMarketIndex()
        await index.initialize(store)

        all_markets = index.get_all_markets()
        assert len(all_markets) == 2
        tickers = {m["market_ticker"] for m in all_markets}
        assert tickers == {"MKT-A1", "MKT-B1"}


class TestInitializeWithAlternativeTicker:
    """Tests for initialize using 'ticker' key instead of 'market_ticker'."""

    @pytest.mark.asyncio
    async def test_initialize_uses_ticker_fallback(self):
        markets = [
            {"event_ticker": "EVT-A", "ticker": "MKT-A1", "yes_bid": "50"},
        ]
        store = MagicMock()
        store.get_all_markets = AsyncMock(return_value=markets)

        index = EventMarketIndex()
        await index.initialize(store)

        assert index.market_count == 1
        assert index.get_market("MKT-A1") is not None


class TestCountKalshiKeysBytes:
    """Tests for _count_kalshi_keys with bytes keys."""

    @pytest.mark.asyncio
    async def test_reconcile_with_bytes_keys(self):
        markets = [_make_market("EVT-A", f"MKT-{i}") for i in range(3)]
        store = MagicMock()
        store.get_all_markets = AsyncMock(return_value=markets)

        index = EventMarketIndex()
        await index.initialize(store)

        redis = MagicMock()
        keys = [
            b"markets:kalshi:MKT-0",
            b"markets:kalshi:MKT-1",
            b"markets:kalshi:MKT-2",
        ]

        async def mock_scan(cursor=0, match="", count=500):
            return 0, keys

        redis.scan = AsyncMock(side_effect=mock_scan)
        assert await index.reconcile(redis) is False

    @pytest.mark.asyncio
    async def test_reconcile_bytes_keys_excludes_subkeys(self):
        markets = [_make_market("EVT-A", f"MKT-{i}") for i in range(2)]
        store = MagicMock()
        store.get_all_markets = AsyncMock(return_value=markets)

        index = EventMarketIndex()
        await index.initialize(store)

        redis = MagicMock()
        keys = [
            b"markets:kalshi:MKT-0",
            b"markets:kalshi:MKT-1",
            b"markets:kalshi:MKT-0:trading_signal",
        ]

        async def mock_scan(cursor=0, match="", count=500):
            return 0, keys

        redis.scan = AsyncMock(side_effect=mock_scan)
        assert await index.reconcile(redis) is False
