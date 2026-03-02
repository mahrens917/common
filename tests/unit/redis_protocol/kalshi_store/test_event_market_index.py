"""Tests for EventMarketIndex."""

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
