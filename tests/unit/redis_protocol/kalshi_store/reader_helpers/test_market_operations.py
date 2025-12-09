"""Tests for market operations module."""

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.common.redis_protocol.kalshi_store.reader_helpers.market_operations import (
    aggregate_strike_data,
    check_market_tracked,
    get_subscribed_markets_safe,
    query_market_for_strike_expiry,
)


class TestGetSubscribedMarketsSafe:
    """Tests for get_subscribed_markets_safe function."""

    @pytest.mark.asyncio
    async def test_delegates_to_snapshot_reader(self) -> None:
        """Delegates to snapshot_reader.get_subscribed_markets."""
        mock_redis = AsyncMock()
        mock_reader = AsyncMock()
        expected_markets = {"KXTEMP-TEST1", "KXTEMP-TEST2"}
        mock_reader.get_subscribed_markets.return_value = expected_markets

        result = await get_subscribed_markets_safe(
            mock_redis, "ops:subscriptions:kalshi", mock_reader
        )

        assert result == expected_markets
        mock_reader.get_subscribed_markets.assert_called_once_with(
            mock_redis, "ops:subscriptions:kalshi"
        )


class TestCheckMarketTracked:
    """Tests for check_market_tracked function."""

    @pytest.mark.asyncio
    async def test_delegates_to_snapshot_reader(self) -> None:
        """Delegates to snapshot_reader.is_market_tracked."""
        mock_redis = AsyncMock()
        mock_reader = AsyncMock()
        mock_reader.is_market_tracked.return_value = True

        result = await check_market_tracked(
            mock_redis, "markets:kalshi:temp:KXTEMP-TEST", "KXTEMP-TEST", mock_reader
        )

        assert result is True
        mock_reader.is_market_tracked.assert_called_once()


class TestQueryMarketForStrikeExpiry:
    """Tests for query_market_for_strike_expiry function."""

    @pytest.mark.asyncio
    async def test_returns_market_data(self) -> None:
        """Returns market data from market lookup."""
        mock_redis = AsyncMock()
        mock_lookup = AsyncMock()
        expected_data = {"ticker": "KXTEMP-TEST", "strike": 50.0}
        mock_lookup.get_market_data_for_strike_expiry.return_value = expected_data
        mock_key_fn = MagicMock(return_value="markets:kalshi:temp:KXTEMP-TEST")

        result = await query_market_for_strike_expiry(
            mock_redis,
            "BTC",
            "2024-12-01",
            50000.0,
            {"KXTEMP-TEST"},
            mock_key_fn,
            mock_lookup,
        )

        assert result == expected_data

    @pytest.mark.asyncio
    async def test_returns_none_on_redis_error(self) -> None:
        """Returns None on Redis error."""
        mock_redis = AsyncMock()
        mock_lookup = AsyncMock()
        from redis.exceptions import ConnectionError

        mock_lookup.get_market_data_for_strike_expiry.side_effect = ConnectionError("Test error")
        mock_key_fn = MagicMock()

        result = await query_market_for_strike_expiry(
            mock_redis,
            "BTC",
            "2024-12-01",
            50000.0,
            {"KXTEMP-TEST"},
            mock_key_fn,
            mock_lookup,
        )

        assert result is None


class TestAggregateStrikeData:
    """Tests for aggregate_strike_data function."""

    @pytest.mark.asyncio
    async def test_aggregates_markets(self) -> None:
        """Aggregates markets into strike summary."""
        mock_aggregator = MagicMock()
        mock_aggregator.aggregate_markets_by_point.return_value = (
            {("2024-12-01", 50.0): ["KXTEMP-TEST"]},
            {"KXTEMP-TEST": {"ticker": "KXTEMP-TEST"}},
        )
        mock_aggregator.build_strike_summary.return_value = {"2024-12-01": [{"strike": 50.0}]}
        mock_logger = MagicMock()

        result = await aggregate_strike_data(
            [{"ticker": "KXTEMP-TEST"}],
            mock_aggregator,
            mock_logger,
            "BTC",
        )

        assert "2024-12-01" in result
        mock_aggregator.aggregate_markets_by_point.assert_called_once()
        mock_aggregator.build_strike_summary.assert_called_once()

    @pytest.mark.asyncio
    async def test_logs_debug_message(self) -> None:
        """Logs debug message about aggregated points."""
        mock_aggregator = MagicMock()
        mock_aggregator.aggregate_markets_by_point.return_value = (
            {("2024-12-01", 50.0): ["KXTEMP-TEST"]},
            {},
        )
        mock_aggregator.build_strike_summary.return_value = {}
        mock_logger = MagicMock()

        await aggregate_strike_data([], mock_aggregator, mock_logger, "BTC")

        mock_logger.debug.assert_called()
