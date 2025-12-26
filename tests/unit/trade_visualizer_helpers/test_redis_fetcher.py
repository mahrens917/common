"""Tests for redis_fetcher module."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.trade_visualizer_helpers.redis_fetcher import RedisFetcher


@pytest.fixture
def mock_trade_store() -> MagicMock:
    """Create a mock TradeStore."""
    store = MagicMock()
    store.get_trade_by_order_id = AsyncMock(return_value=None)
    return store


@pytest.fixture
def mock_redis() -> MagicMock:
    """Create a mock Redis client."""
    redis = MagicMock()
    redis.smembers = AsyncMock(return_value=[])
    redis.keys = AsyncMock(return_value=[])
    redis.hgetall = AsyncMock(return_value={})
    return redis


class TestRedisFetcher:
    """Tests for RedisFetcher class."""

    def test_init(self, mock_trade_store: MagicMock) -> None:
        """Test RedisFetcher initialization."""
        fetcher = RedisFetcher(mock_trade_store)

        assert fetcher._trade_store is mock_trade_store

    @pytest.mark.asyncio
    async def test_get_executed_trades_empty(
        self,
        mock_trade_store: MagicMock,
        mock_redis: MagicMock,
    ) -> None:
        """Test getting executed trades when none exist."""
        fetcher = RedisFetcher(mock_trade_store)
        start = datetime(2024, 12, 25, 0, 0, tzinfo=timezone.utc)
        end = datetime(2024, 12, 25, 23, 59, tzinfo=timezone.utc)

        result = await fetcher.get_executed_trades_for_station(mock_redis, "KJFK", start, end)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_executed_trades_with_trades(
        self,
        mock_trade_store: MagicMock,
        mock_redis: MagicMock,
    ) -> None:
        """Test getting executed trades with valid trades."""
        mock_redis.smembers.return_value = [b"order_123"]
        mock_trade = MagicMock()
        mock_trade.trade_timestamp = datetime(2024, 12, 25, 12, 0, tzinfo=timezone.utc)
        mock_trade_store.get_trade_by_order_id.return_value = mock_trade

        fetcher = RedisFetcher(mock_trade_store)
        start = datetime(2024, 12, 25, 0, 0, tzinfo=timezone.utc)
        end = datetime(2024, 12, 25, 23, 59, tzinfo=timezone.utc)

        result = await fetcher.get_executed_trades_for_station(mock_redis, "KJFK", start, end)

        assert len(result) == 1
        assert result[0] is mock_trade

    @pytest.mark.asyncio
    async def test_get_executed_trades_filters_by_time(
        self,
        mock_trade_store: MagicMock,
        mock_redis: MagicMock,
    ) -> None:
        """Test trades outside time range are filtered."""
        mock_redis.smembers.return_value = [b"order_123"]
        mock_trade = MagicMock()
        mock_trade.trade_timestamp = datetime(2024, 12, 24, 12, 0, tzinfo=timezone.utc)
        mock_trade_store.get_trade_by_order_id.return_value = mock_trade

        fetcher = RedisFetcher(mock_trade_store)
        start = datetime(2024, 12, 25, 0, 0, tzinfo=timezone.utc)
        end = datetime(2024, 12, 25, 23, 59, tzinfo=timezone.utc)

        result = await fetcher.get_executed_trades_for_station(mock_redis, "KJFK", start, end)

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_market_liquidity_states_non_kmia(
        self,
        mock_trade_store: MagicMock,
        mock_redis: MagicMock,
    ) -> None:
        """Test get_market_liquidity_states returns empty for non-KMIA stations."""
        fetcher = RedisFetcher(mock_trade_store)
        start = datetime(2024, 12, 25, 0, 0, tzinfo=timezone.utc)
        end = datetime(2024, 12, 25, 23, 59, tzinfo=timezone.utc)

        result = await fetcher.get_market_liquidity_states(mock_redis, "KJFK", start, end)

        assert result == []

    def test_is_auxiliary_key_trading_signal(self, mock_trade_store: MagicMock) -> None:
        """Test _is_auxiliary_key returns True for trading_signal keys."""
        fetcher = RedisFetcher(mock_trade_store)

        result = fetcher._is_auxiliary_key("kalshi:market:trading_signal")

        assert result is True

    def test_is_auxiliary_key_position_state(self, mock_trade_store: MagicMock) -> None:
        """Test _is_auxiliary_key returns True for position_state keys."""
        fetcher = RedisFetcher(mock_trade_store)

        result = fetcher._is_auxiliary_key("kalshi:market:position_state")

        assert result is True

    def test_is_auxiliary_key_normal_key(self, mock_trade_store: MagicMock) -> None:
        """Test _is_auxiliary_key returns False for normal keys."""
        fetcher = RedisFetcher(mock_trade_store)

        result = fetcher._is_auxiliary_key("kalshi:market:KXHIGHFL")

        assert result is False

    def test_decode_market_data_bytes(self, mock_trade_store: MagicMock) -> None:
        """Test _decode_market_data decodes bytes."""
        fetcher = RedisFetcher(mock_trade_store)
        market_data = {b"ticker": b"KXHIGH", b"price": b"50"}

        result = fetcher._decode_market_data(market_data)

        assert result == {"ticker": "KXHIGH", "price": "50"}

    def test_decode_market_data_strings(self, mock_trade_store: MagicMock) -> None:
        """Test _decode_market_data handles strings."""
        fetcher = RedisFetcher(mock_trade_store)
        market_data = {"ticker": "KXHIGH", "price": "50"}

        result = fetcher._decode_market_data(market_data)

        assert result == {"ticker": "KXHIGH", "price": "50"}

    def test_safe_float_valid(self, mock_trade_store: MagicMock) -> None:
        """Test _safe_float with valid value."""
        fetcher = RedisFetcher(mock_trade_store)

        result = fetcher._safe_float("50.5")

        assert result == 50.5

    def test_safe_float_none(self, mock_trade_store: MagicMock) -> None:
        """Test _safe_float with None."""
        fetcher = RedisFetcher(mock_trade_store)

        result = fetcher._safe_float(None)

        assert result is None

    def test_safe_float_invalid(self, mock_trade_store: MagicMock) -> None:
        """Test _safe_float with invalid value."""
        fetcher = RedisFetcher(mock_trade_store)

        result = fetcher._safe_float("invalid")

        assert result is None

    def test_build_market_state(self, mock_trade_store: MagicMock) -> None:
        """Test _build_market_state creates state."""
        fetcher = RedisFetcher(mock_trade_store)
        decoded = {
            "yes_bid": "45",
            "yes_ask": "55",
            "traded": "true",
            "floor_strike": "40",
            "cap_strike": "60",
        }

        result = fetcher._build_market_state("KXHIGHFL-T50", decoded)

        assert result.market_ticker == "KXHIGHFL-T50"
        assert result.yes_bid == 45.0
        assert result.yes_ask == 55.0
        assert result.traded is True

    def test_build_market_state_missing_traded(self, mock_trade_store: MagicMock) -> None:
        """Test _build_market_state raises on missing traded field."""
        fetcher = RedisFetcher(mock_trade_store)
        decoded = {"yes_bid": "45", "yes_ask": "55"}

        with pytest.raises(ValueError, match="missing 'traded' field"):
            fetcher._build_market_state("KXHIGHFL-T50", decoded)
