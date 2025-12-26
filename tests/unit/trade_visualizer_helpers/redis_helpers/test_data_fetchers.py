"""Tests for trade_visualizer_helpers.redis_helpers.data_fetchers module."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.trade_visualizer_helpers.redis_helpers.data_fetchers import (
    get_executed_trades_for_station,
    get_market_liquidity_states,
)


class TestGetExecutedTradesForStation:
    """Tests for get_executed_trades_for_station function."""

    @pytest.mark.asyncio
    async def test_fetches_trades(self) -> None:
        """Test fetches trades and closes connection."""
        mock_redis = MagicMock()
        mock_redis.aclose = AsyncMock()
        mock_fetcher = MagicMock()
        mock_fetcher.get_executed_trades_for_station = AsyncMock(return_value=["trade1", "trade2"])
        start_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2025, 1, 15, 18, 0, 0, tzinfo=timezone.utc)

        with patch(
            "common.trade_visualizer_helpers.redis_helpers.data_fetchers.get_redis_connection",
            new_callable=AsyncMock,
            return_value=mock_redis,
        ):
            result = await get_executed_trades_for_station(mock_fetcher, "KJFK", start_time, end_time)

        assert result == ["trade1", "trade2"]
        mock_redis.aclose.assert_called_once()


class TestGetMarketLiquidityStates:
    """Tests for get_market_liquidity_states function."""

    @pytest.mark.asyncio
    async def test_fetches_liquidity_states(self) -> None:
        """Test fetches liquidity states and closes connection."""
        mock_redis = MagicMock()
        mock_redis.aclose = AsyncMock()
        mock_fetcher = MagicMock()
        mock_fetcher.get_market_liquidity_states = AsyncMock(return_value=[MagicMock(), MagicMock()])
        start_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2025, 1, 15, 18, 0, 0, tzinfo=timezone.utc)

        with patch(
            "common.trade_visualizer_helpers.redis_helpers.data_fetchers.get_redis_connection",
            new_callable=AsyncMock,
            return_value=mock_redis,
        ):
            result = await get_market_liquidity_states(mock_fetcher, "KJFK", start_time, end_time)

        assert len(result) == 2
        mock_redis.aclose.assert_called_once()
