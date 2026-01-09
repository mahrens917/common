"""Tests for ownership_helpers module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.redis_protocol.market_update_api_helpers.ownership_helpers import (
    OwnershipCheckResult,
    algo_field,
    check_ownership,
    clear_algo_ownership,
    clear_stale_markets,
    get_market_algo,
    record_rejection,
    scan_algo_owned_markets,
)


class TestAlgoField:
    """Tests for algo_field function."""

    def test_builds_namespaced_field(self):
        result = algo_field("weather", "t_yes_bid")
        assert result == "weather:t_yes_bid"

    def test_builds_namespaced_field_with_ask(self):
        result = algo_field("pdf", "t_yes_ask")
        assert result == "pdf:t_yes_ask"


class TestCheckOwnership:
    """Tests for check_ownership function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.hget = AsyncMock(return_value=None)
        redis.hincrby = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_no_owner_returns_success(self, mock_redis):
        result = await check_ownership(mock_redis, "market:key", "weather", "TICKER")
        assert result.success is True
        assert result.rejected is False
        assert result.owning_algo == "weather"

    @pytest.mark.asyncio
    async def test_same_owner_returns_success(self, mock_redis):
        mock_redis.hget = AsyncMock(return_value=b"weather")
        result = await check_ownership(mock_redis, "market:key", "weather", "TICKER")
        assert result.success is True
        assert result.rejected is False

    @pytest.mark.asyncio
    async def test_different_owner_returns_rejection(self, mock_redis):
        mock_redis.hget = AsyncMock(return_value=b"pdf")
        result = await check_ownership(mock_redis, "market:key", "weather", "TICKER")
        assert result.success is False
        assert result.rejected is True
        assert result.reason == "owned_by_pdf"
        assert result.owning_algo == "pdf"

    @pytest.mark.asyncio
    async def test_string_owner_returns_rejection(self, mock_redis):
        mock_redis.hget = AsyncMock(return_value="pdf")
        result = await check_ownership(mock_redis, "market:key", "weather", "TICKER")
        assert result.success is False
        assert result.rejected is True


class TestRecordRejection:
    """Tests for record_rejection function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.hincrby = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_records_rejection(self, mock_redis):
        await record_rejection(mock_redis, "pdf", "weather")
        mock_redis.hincrby.assert_called_once()
        call_args = mock_redis.hincrby.call_args
        assert "algo_rejections:" in call_args[0][0]
        assert call_args[0][1] == "pdf:weather"
        assert call_args[0][2] == 1


class TestGetMarketAlgo:
    """Tests for get_market_algo function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.hget = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_no_algo(self, mock_redis):
        mock_redis.hget = AsyncMock(return_value=None)
        result = await get_market_algo(mock_redis, "market:key")
        assert result is None

    @pytest.mark.asyncio
    async def test_bytes_algo(self, mock_redis):
        mock_redis.hget = AsyncMock(return_value=b"weather")
        result = await get_market_algo(mock_redis, "market:key")
        assert result == "weather"

    @pytest.mark.asyncio
    async def test_string_algo(self, mock_redis):
        mock_redis.hget = AsyncMock(return_value="pdf")
        result = await get_market_algo(mock_redis, "market:key")
        assert result == "pdf"


class TestScanAlgoOwnedMarkets:
    """Tests for scan_algo_owned_markets function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.scan = AsyncMock()
        redis.hget = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_no_markets_found(self, mock_redis):
        mock_redis.scan = AsyncMock(return_value=(0, []))
        result = await scan_algo_owned_markets(mock_redis, "markets:kalshi:*", "weather")
        assert result == set()

    @pytest.mark.asyncio
    async def test_finds_owned_markets(self, mock_redis):
        mock_redis.scan = AsyncMock(return_value=(0, [b"markets:kalshi:weather:TICKER1", b"markets:kalshi:weather:TICKER2"]))
        mock_redis.hget = AsyncMock(return_value=b"weather")

        result = await scan_algo_owned_markets(mock_redis, "markets:kalshi:*", "weather")

        assert "TICKER1" in result
        assert "TICKER2" in result

    @pytest.mark.asyncio
    async def test_skips_markets_owned_by_other_algo(self, mock_redis):
        mock_redis.scan = AsyncMock(return_value=(0, [b"markets:kalshi:weather:TICKER1", b"markets:kalshi:weather:TICKER2"]))

        async def hget_side_effect(key, field):
            if "TICKER1" in key:
                return b"weather"
            return b"pdf"

        mock_redis.hget = AsyncMock(side_effect=hget_side_effect)

        result = await scan_algo_owned_markets(mock_redis, "markets:kalshi:*", "weather")

        assert "TICKER1" in result
        assert "TICKER2" not in result

    @pytest.mark.asyncio
    async def test_skips_markets_with_no_owner(self, mock_redis):
        mock_redis.scan = AsyncMock(return_value=(0, [b"markets:kalshi:weather:TICKER1"]))
        mock_redis.hget = AsyncMock(return_value=None)

        result = await scan_algo_owned_markets(mock_redis, "markets:kalshi:*", "weather")

        assert result == set()

    @pytest.mark.asyncio
    async def test_handles_multiple_scan_iterations(self, mock_redis):
        # First call returns cursor 100, second call returns cursor 0
        mock_redis.scan = AsyncMock(
            side_effect=[
                (100, [b"markets:kalshi:weather:TICKER1"]),
                (0, [b"markets:kalshi:weather:TICKER2"]),
            ]
        )
        mock_redis.hget = AsyncMock(return_value=b"weather")

        result = await scan_algo_owned_markets(mock_redis, "markets:kalshi:*", "weather")

        assert "TICKER1" in result
        assert "TICKER2" in result
        assert mock_redis.scan.call_count == 2

    @pytest.mark.asyncio
    async def test_handles_string_keys(self, mock_redis):
        mock_redis.scan = AsyncMock(return_value=(0, ["markets:kalshi:weather:TICKER1"]))
        mock_redis.hget = AsyncMock(return_value="weather")

        result = await scan_algo_owned_markets(mock_redis, "markets:kalshi:*", "weather")

        assert "TICKER1" in result


class TestClearStaleMarkets:
    """Tests for clear_stale_markets function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.hget = AsyncMock()
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
    async def test_clears_owned_markets(self, mock_redis, key_builder):
        mock_redis.hget = AsyncMock(return_value=b"weather")

        result = await clear_stale_markets(mock_redis, {"TICKER1", "TICKER2"}, "weather", key_builder)

        assert len(result) == 2
        assert "TICKER1" in result
        assert "TICKER2" in result
        assert mock_redis.hdel.call_count == 2

    @pytest.mark.asyncio
    async def test_skips_markets_owned_by_other_algo(self, mock_redis, key_builder):
        async def hget_side_effect(key, field):
            if "TICKER1" in key:
                return b"weather"
            return b"pdf"

        mock_redis.hget = AsyncMock(side_effect=hget_side_effect)

        result = await clear_stale_markets(mock_redis, {"TICKER1", "TICKER2"}, "weather", key_builder)

        assert result == ["TICKER1"]
        mock_redis.hdel.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_unowned_markets(self, mock_redis, key_builder):
        mock_redis.hget = AsyncMock(return_value=None)

        result = await clear_stale_markets(mock_redis, {"TICKER1"}, "weather", key_builder)

        assert result == []
        mock_redis.hdel.assert_not_called()


class TestClearAlgoOwnership:
    """Tests for clear_algo_ownership function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.hdel = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_clears_existing_ownership(self, mock_redis):
        mock_redis.hdel = AsyncMock(return_value=1)
        result = await clear_algo_ownership(mock_redis, "market:key")
        assert result is True
        mock_redis.hdel.assert_called_once_with("market:key", "algo")

    @pytest.mark.asyncio
    async def test_clears_nonexistent_ownership(self, mock_redis):
        mock_redis.hdel = AsyncMock(return_value=0)
        result = await clear_algo_ownership(mock_redis, "market:key")
        assert result is False


class TestOwnershipCheckResult:
    """Tests for OwnershipCheckResult dataclass."""

    def test_create_success_result(self):
        result = OwnershipCheckResult(success=True, rejected=False, reason=None, owning_algo="weather")
        assert result.success is True
        assert result.rejected is False
        assert result.reason is None
        assert result.owning_algo == "weather"

    def test_create_rejected_result(self):
        result = OwnershipCheckResult(success=False, rejected=True, reason="owned_by_pdf", owning_algo="pdf")
        assert result.success is False
        assert result.rejected is True
        assert result.reason == "owned_by_pdf"
        assert result.owning_algo == "pdf"
