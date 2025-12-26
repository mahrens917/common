"""Tests for trade_visualizer_helpers.trade_fetcher module."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.trade_visualizer_helpers.trade_fetcher import TradeFetcher


class TestTradeFetcherInit:
    """Tests for TradeFetcher initialization."""

    def test_init_stores_trade_store(self) -> None:
        """Test initialization stores trade store."""
        mock_store = MagicMock()

        fetcher = TradeFetcher(mock_store)

        assert fetcher._trade_store == mock_store


class TestTradeFetcherEnsureAware:
    """Tests for _ensure_aware static method."""

    def test_already_aware_timestamp(self) -> None:
        """Test timestamp that's already aware is returned."""
        aware_ts = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        result = TradeFetcher._ensure_aware(aware_ts)

        assert result == aware_ts
        assert result.tzinfo is not None

    def test_naive_timestamp_becomes_aware(self) -> None:
        """Test naive timestamp becomes UTC aware."""
        naive_ts = datetime(2025, 1, 1, 12, 0, 0)

        result = TradeFetcher._ensure_aware(naive_ts)

        assert result.tzinfo is not None
        assert result.hour == 12


class TestTradeFetcherNormalizeRange:
    """Tests for _normalize_range static method."""

    def test_normalizes_both_timestamps(self) -> None:
        """Test normalizes both start and end timestamps."""
        start = datetime(2025, 1, 1, 10, 0, 0)
        end = datetime(2025, 1, 1, 14, 0, 0)

        start_aware, end_aware = TradeFetcher._normalize_range(start, end)

        assert start_aware.tzinfo is not None
        assert end_aware.tzinfo is not None


class TestTradeFetcherCollectTrades:
    """Tests for _collect_trades method."""

    @pytest.mark.asyncio
    async def test_collects_trades_in_range(self) -> None:
        """Test collects trades within time range."""
        mock_store = MagicMock()
        mock_trade = MagicMock()
        mock_trade.trade_timestamp = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_store.get_trade_by_order_id = AsyncMock(return_value=mock_trade)

        fetcher = TradeFetcher(mock_store)
        start = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 1, 1, 14, 0, 0, tzinfo=timezone.utc)

        result = await fetcher._collect_trades(["order-1"], start, end)

        assert len(result) == 1
        assert result[0] == mock_trade

    @pytest.mark.asyncio
    async def test_skips_trades_outside_range(self) -> None:
        """Test skips trades outside time range."""
        mock_store = MagicMock()
        mock_trade = MagicMock()
        mock_trade.trade_timestamp = datetime(2025, 1, 1, 8, 0, 0, tzinfo=timezone.utc)
        mock_store.get_trade_by_order_id = AsyncMock(return_value=mock_trade)

        fetcher = TradeFetcher(mock_store)
        start = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 1, 1, 14, 0, 0, tzinfo=timezone.utc)

        result = await fetcher._collect_trades(["order-1"], start, end)

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_skips_none_trades(self) -> None:
        """Test skips None trades."""
        mock_store = MagicMock()
        mock_store.get_trade_by_order_id = AsyncMock(return_value=None)

        fetcher = TradeFetcher(mock_store)
        start = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 1, 1, 14, 0, 0, tzinfo=timezone.utc)

        result = await fetcher._collect_trades(["order-1"], start, end)

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_handles_bytes_order_ids(self) -> None:
        """Test handles bytes order IDs."""
        mock_store = MagicMock()
        mock_trade = MagicMock()
        mock_trade.trade_timestamp = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_store.get_trade_by_order_id = AsyncMock(return_value=mock_trade)

        fetcher = TradeFetcher(mock_store)
        start = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 1, 1, 14, 0, 0, tzinfo=timezone.utc)

        result = await fetcher._collect_trades([b"order-1"], start, end)

        assert len(result) == 1
        mock_store.get_trade_by_order_id.assert_called_with("order-1")


class TestTradeFetcherGetExecutedTradesForStation:
    """Tests for get_executed_trades_for_station method."""

    @pytest.mark.asyncio
    async def test_fetches_trades_for_station(self) -> None:
        """Test fetches trades for a station."""
        mock_store = MagicMock()
        mock_trade = MagicMock()
        mock_trade.trade_timestamp = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_store.get_trade_by_order_id = AsyncMock(return_value=mock_trade)

        mock_redis = MagicMock()
        mock_redis.smembers = AsyncMock(return_value=[b"order-1"])
        mock_redis.aclose = AsyncMock()

        fetcher = TradeFetcher(mock_store)
        start = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 1, 1, 14, 0, 0, tzinfo=timezone.utc)

        with patch(
            "common.trade_visualizer_helpers.trade_fetcher.get_redis_connection",
            return_value=mock_redis,
        ):
            result = await fetcher.get_executed_trades_for_station("KMIA", start, end)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_handles_connection_error(self) -> None:
        """Test handles connection error gracefully."""
        mock_store = MagicMock()
        fetcher = TradeFetcher(mock_store)
        start = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 1, 1, 14, 0, 0, tzinfo=timezone.utc)

        with patch(
            "common.trade_visualizer_helpers.trade_fetcher.get_redis_connection",
            side_effect=ConnectionError("Failed"),
        ):
            result = await fetcher.get_executed_trades_for_station("KMIA", start, end)

        assert result == []

    @pytest.mark.asyncio
    async def test_handles_os_error(self) -> None:
        """Test handles OS error gracefully."""
        mock_store = MagicMock()
        fetcher = TradeFetcher(mock_store)
        start = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 1, 1, 14, 0, 0, tzinfo=timezone.utc)

        with patch(
            "common.trade_visualizer_helpers.trade_fetcher.get_redis_connection",
            side_effect=OSError("Network error"),
        ):
            result = await fetcher.get_executed_trades_for_station("KMIA", start, end)

        assert result == []

    @pytest.mark.asyncio
    async def test_closes_redis_connection(self) -> None:
        """Test closes Redis connection after use."""
        mock_store = MagicMock()
        mock_store.get_trade_by_order_id = AsyncMock(return_value=None)

        mock_redis = MagicMock()
        mock_redis.smembers = AsyncMock(return_value=[])
        mock_redis.aclose = AsyncMock()

        fetcher = TradeFetcher(mock_store)
        start = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 1, 1, 14, 0, 0, tzinfo=timezone.utc)

        with patch(
            "common.trade_visualizer_helpers.trade_fetcher.get_redis_connection",
            return_value=mock_redis,
        ):
            await fetcher.get_executed_trades_for_station("KMIA", start, end)

        mock_redis.aclose.assert_called_once()
