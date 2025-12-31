"""Tests for market_update_api module."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.redis_protocol.market_update_api import (
    VALID_ALGOS,
    MarketUpdateResult,
    clear_algo_ownership,
    compute_direction,
    get_market_algo,
    get_rejection_stats,
    request_market_update,
)


class TestComputeDirection:
    """Tests for compute_direction function."""

    def test_buy_signal_when_kalshi_ask_below_theoretical(self):
        result = compute_direction(t_yes_bid=None, t_yes_ask=92, kalshi_bid=1, kalshi_ask=11)
        assert result == "BUY"

    def test_sell_signal_when_kalshi_bid_above_theoretical(self):
        result = compute_direction(t_yes_bid=10, t_yes_ask=None, kalshi_bid=15, kalshi_ask=20)
        assert result == "SELL"

    def test_none_when_both_conditions_true(self):
        result = compute_direction(t_yes_bid=5, t_yes_ask=95, kalshi_bid=10, kalshi_ask=90)
        assert result == "NONE"

    def test_none_when_neither_condition_true(self):
        result = compute_direction(t_yes_bid=10, t_yes_ask=50, kalshi_bid=5, kalshi_ask=55)
        assert result == "NONE"

    def test_none_when_no_theoretical_prices(self):
        result = compute_direction(t_yes_bid=None, t_yes_ask=None, kalshi_bid=10, kalshi_ask=20)
        assert result == "NONE"

    def test_none_when_kalshi_ask_is_zero(self):
        result = compute_direction(t_yes_bid=None, t_yes_ask=50, kalshi_bid=0, kalshi_ask=0)
        assert result == "NONE"


class TestRequestMarketUpdate:
    """Tests for request_market_update function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.hget = AsyncMock(return_value=None)
        redis.hset = AsyncMock()
        redis.hmget = AsyncMock(return_value=[b"10", b"20"])  # yes_bid=10, yes_ask=20
        redis.hincrby = AsyncMock()
        redis.publish = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_invalid_algo_raises_value_error(self, mock_redis):
        with pytest.raises(ValueError, match="Invalid algo"):
            await request_market_update(mock_redis, "market:key", "invalid_algo", 50.0, 55.0)

    @pytest.mark.asyncio
    async def test_no_prices_provided_returns_no_success(self, mock_redis):
        result = await request_market_update(mock_redis, "market:key", "weather", None, None)

        assert result.success is False
        assert result.rejected is False
        assert result.reason == "no_prices_provided"

    @pytest.mark.asyncio
    async def test_first_update_succeeds(self, mock_redis):
        result = await request_market_update(mock_redis, "market:key", "weather", 50.0, 55.0)

        assert result.success is True
        assert result.rejected is False
        assert result.owning_algo == "weather"
        mock_redis.hset.assert_called_once()

    @pytest.mark.asyncio
    async def test_same_algo_update_succeeds(self, mock_redis):
        mock_redis.hget = AsyncMock(return_value=b"weather")

        result = await request_market_update(mock_redis, "market:key", "weather", 50.0, 55.0)

        assert result.success is True
        assert result.rejected is False

    @pytest.mark.asyncio
    async def test_different_algo_update_rejected(self, mock_redis):
        mock_redis.hget = AsyncMock(return_value=b"weather")

        result = await request_market_update(mock_redis, "market:key", "pdf", 50.0, 55.0)

        assert result.success is False
        assert result.rejected is True
        assert result.reason == "owned_by_weather"
        assert result.owning_algo == "weather"

    @pytest.mark.asyncio
    async def test_update_with_only_bid_deletes_ask(self, mock_redis):
        mock_redis.hdel = AsyncMock()

        result = await request_market_update(mock_redis, "market:key", "peak", 50.0, None)

        assert result.success is True
        mock_redis.hset.assert_called_once()
        mock_redis.hdel.assert_called_once_with("market:key", "t_yes_ask")

    @pytest.mark.asyncio
    async def test_update_with_only_ask_deletes_bid(self, mock_redis):
        mock_redis.hdel = AsyncMock()

        result = await request_market_update(mock_redis, "market:key", "extreme", None, 55.0)

        assert result.success is True
        mock_redis.hset.assert_called_once()
        mock_redis.hdel.assert_called_once_with("market:key", "t_yes_bid")

    @pytest.mark.asyncio
    async def test_update_with_both_prices_keeps_both(self, mock_redis):
        mock_redis.hdel = AsyncMock()

        result = await request_market_update(mock_redis, "market:key", "pdf", 50.0, 55.0)

        assert result.success is True
        mock_redis.hset.assert_called_once()
        # When both prices provided, neither should be deleted
        mock_redis.hdel.assert_not_called()

    @pytest.mark.asyncio
    async def test_ticker_extracted_from_key(self, mock_redis):
        result = await request_market_update(mock_redis, "markets:kalshi:weather:TICKER123", "weather", 50.0, 55.0)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_ticker_provided_explicitly(self, mock_redis):
        result = await request_market_update(mock_redis, "market:key", "weather", 50.0, 55.0, ticker="CUSTOM")

        assert result.success is True

    @pytest.mark.asyncio
    async def test_string_algo_ownership(self, mock_redis):
        mock_redis.hget = AsyncMock(return_value="weather")

        result = await request_market_update(mock_redis, "market:key", "weather", 50.0, 55.0)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_publishes_market_event_update_when_event_ticker_exists(self, mock_redis):
        def hget_side_effect(key, field):
            if field == "event_ticker":
                return b"KXHIGH-KDCA-20250101"
            return None

        mock_redis.hget = AsyncMock(side_effect=hget_side_effect)

        result = await request_market_update(mock_redis, "market:key", "weather", 50.0, 55.0)

        assert result.success is True
        mock_redis.publish.assert_called_once()
        call_args = mock_redis.publish.call_args
        assert call_args[0][0] == "market_event_updates:KXHIGH-KDCA-20250101"

    @pytest.mark.asyncio
    async def test_skips_publish_when_no_event_ticker(self, mock_redis):
        result = await request_market_update(mock_redis, "market:key", "weather", 50.0, 55.0)

        assert result.success is True
        mock_redis.publish.assert_not_called()


class TestGetRejectionStats:
    """Tests for get_rejection_stats function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.hgetall = AsyncMock(return_value={})
        return redis

    @pytest.mark.asyncio
    async def test_no_rejections(self, mock_redis):
        result = await get_rejection_stats(mock_redis)

        assert result == {}

    @pytest.mark.asyncio
    async def test_with_rejections(self, mock_redis):
        today = date.today().isoformat()
        mock_redis.hgetall = AsyncMock(return_value={b"weather:pdf": b"5", b"peak:extreme": b"3"})

        result = await get_rejection_stats(mock_redis, days=1)

        assert today in result
        assert result[today]["weather:pdf"] == 5
        assert result[today]["peak:extreme"] == 3

    @pytest.mark.asyncio
    async def test_multiple_days(self, mock_redis):
        mock_redis.hgetall = AsyncMock(return_value={b"weather:pdf": b"2"})

        result = await get_rejection_stats(mock_redis, days=3)

        # Should have checked 3 days
        assert mock_redis.hgetall.call_count == 3

    @pytest.mark.asyncio
    async def test_string_field_handling(self, mock_redis):
        mock_redis.hgetall = AsyncMock(return_value={"weather:pdf": "10"})

        result = await get_rejection_stats(mock_redis, days=1)

        today = date.today().isoformat()
        assert result[today]["weather:pdf"] == 10


class TestClearAlgoOwnership:
    """Tests for clear_algo_ownership function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.hdel = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_clear_existing_ownership(self, mock_redis):
        mock_redis.hdel = AsyncMock(return_value=1)

        result = await clear_algo_ownership(mock_redis, "market:key")

        assert result is True
        mock_redis.hdel.assert_called_once_with("market:key", "algo")

    @pytest.mark.asyncio
    async def test_clear_nonexistent_ownership(self, mock_redis):
        mock_redis.hdel = AsyncMock(return_value=0)

        result = await clear_algo_ownership(mock_redis, "market:key")

        assert result is False


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


class TestMarketUpdateResult:
    """Tests for MarketUpdateResult dataclass."""

    def test_create_success_result(self):
        result = MarketUpdateResult(success=True, rejected=False, reason=None, owning_algo="weather")

        assert result.success is True
        assert result.rejected is False
        assert result.reason is None
        assert result.owning_algo == "weather"

    def test_create_rejected_result(self):
        result = MarketUpdateResult(success=False, rejected=True, reason="owned_by_pdf", owning_algo="pdf")

        assert result.success is False
        assert result.rejected is True
        assert result.reason == "owned_by_pdf"
        assert result.owning_algo == "pdf"


class TestValidAlgos:
    """Tests for VALID_ALGOS constant."""

    def test_all_algos_present(self):
        assert "weather" in VALID_ALGOS
        assert "pdf" in VALID_ALGOS
        assert "peak" in VALID_ALGOS
        assert "extreme" in VALID_ALGOS

    def test_is_frozenset(self):
        assert isinstance(VALID_ALGOS, frozenset)
