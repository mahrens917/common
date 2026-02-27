"""Tests for ownership_helpers module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.redis_protocol.market_update_api_helpers.ownership_helpers import (
    algo_field,
    clear_stale_markets,
    scan_algo_active_markets,
)


class TestAlgoField:
    """Tests for algo_field function."""

    def test_builds_namespaced_field(self):
        result = algo_field("weather", "t_yes_bid")
        assert result == "weather:t_yes_bid"

    def test_builds_namespaced_field_with_ask(self):
        result = algo_field("pdf", "t_yes_ask")
        assert result == "pdf:t_yes_ask"


class TestScanAlgoActiveMarkets:
    """Tests for scan_algo_active_markets function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.scan = AsyncMock()
        redis.hmget = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_no_markets_found(self, mock_redis):
        mock_redis.scan = AsyncMock(return_value=(0, []))
        result = await scan_algo_active_markets(mock_redis, "markets:kalshi:*", "weather")
        assert result == set()

    @pytest.mark.asyncio
    async def test_finds_active_markets(self, mock_redis):
        mock_redis.scan = AsyncMock(return_value=(0, [b"markets:kalshi:weather:TICKER1", b"markets:kalshi:weather:TICKER2"]))
        mock_redis.hmget = AsyncMock(return_value=[b"50", b"55"])

        result = await scan_algo_active_markets(mock_redis, "markets:kalshi:*", "weather")

        assert "TICKER1" in result
        assert "TICKER2" in result

    @pytest.mark.asyncio
    async def test_skips_markets_with_no_prices(self, mock_redis):
        mock_redis.scan = AsyncMock(return_value=(0, [b"markets:kalshi:weather:TICKER1"]))
        mock_redis.hmget = AsyncMock(return_value=[None, None])

        result = await scan_algo_active_markets(mock_redis, "markets:kalshi:*", "weather")

        assert result == set()

    @pytest.mark.asyncio
    async def test_finds_market_with_bid_only(self, mock_redis):
        mock_redis.scan = AsyncMock(return_value=(0, [b"markets:kalshi:weather:TICKER1"]))
        mock_redis.hmget = AsyncMock(return_value=[b"50", None])

        result = await scan_algo_active_markets(mock_redis, "markets:kalshi:*", "weather")

        assert "TICKER1" in result

    @pytest.mark.asyncio
    async def test_finds_market_with_ask_only(self, mock_redis):
        mock_redis.scan = AsyncMock(return_value=(0, [b"markets:kalshi:weather:TICKER1"]))
        mock_redis.hmget = AsyncMock(return_value=[None, b"55"])

        result = await scan_algo_active_markets(mock_redis, "markets:kalshi:*", "weather")

        assert "TICKER1" in result

    @pytest.mark.asyncio
    async def test_handles_multiple_scan_iterations(self, mock_redis):
        mock_redis.scan = AsyncMock(
            side_effect=[
                (100, [b"markets:kalshi:weather:TICKER1"]),
                (0, [b"markets:kalshi:weather:TICKER2"]),
            ]
        )
        mock_redis.hmget = AsyncMock(return_value=[b"50", b"55"])

        result = await scan_algo_active_markets(mock_redis, "markets:kalshi:*", "weather")

        assert "TICKER1" in result
        assert "TICKER2" in result
        _EXPECTED_SCAN_CALLS = 2
        assert mock_redis.scan.call_count == _EXPECTED_SCAN_CALLS

    @pytest.mark.asyncio
    async def test_handles_string_keys(self, mock_redis):
        mock_redis.scan = AsyncMock(return_value=(0, ["markets:kalshi:weather:TICKER1"]))
        mock_redis.hmget = AsyncMock(return_value=[b"50", None])

        result = await scan_algo_active_markets(mock_redis, "markets:kalshi:*", "weather")

        assert "TICKER1" in result


class TestClearStaleMarkets:
    """Tests for clear_stale_markets function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.hdel = AsyncMock()
        return redis

    @pytest.fixture
    def key_builder(self):
        return lambda ticker: f"markets:kalshi:weather:{ticker}"

    @pytest.mark.asyncio
    async def test_empty_stale_tickers(self, mock_redis, key_builder):
        result = await clear_stale_markets(mock_redis, set(), "weather", key_builder)
        assert result == []
        mock_redis.hdel.assert_not_called()

    @pytest.mark.asyncio
    async def test_clears_stale_markets(self, mock_redis, key_builder):
        result = await clear_stale_markets(mock_redis, {"TICKER1", "TICKER2"}, "weather", key_builder)

        assert len(result) == 2
        assert "TICKER1" in result
        assert "TICKER2" in result
        _EXPECTED_HDEL_CALLS = 2
        assert mock_redis.hdel.call_count == _EXPECTED_HDEL_CALLS

    @pytest.mark.asyncio
    async def test_clears_all_namespaced_fields(self, mock_redis, key_builder):
        await clear_stale_markets(mock_redis, {"TICKER1"}, "weather", key_builder)

        call_args = mock_redis.hdel.call_args[0]
        assert call_args[0] == "markets:kalshi:weather:TICKER1"
        assert "weather:t_bid" in call_args
        assert "weather:t_ask" in call_args
        assert "weather:direction" in call_args
        assert "weather:status" in call_args
        assert "weather:reason" in call_args

    @pytest.mark.asyncio
    async def test_clears_metadata_fields(self, mock_redis, key_builder):
        metadata_fields = frozenset({"t_spread", "svi_rmse"})
        await clear_stale_markets(mock_redis, {"TICKER1"}, "pdf", key_builder, metadata_fields)

        call_args = mock_redis.hdel.call_args[0]
        assert "pdf:t_bid" in call_args
        assert "pdf:t_ask" in call_args
        assert "pdf:t_spread" in call_args
        assert "pdf:svi_rmse" in call_args
