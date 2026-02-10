"""Tests for market_update_api module."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from common.redis_protocol.market_update_api import (
    BatchUpdateResult,
    MarketUpdateResult,
    _execute_batch_transaction,
    batch_update_market_signals,
    clear_algo_ownership,
    compute_direction,
    get_market_algo,
    get_rejection_stats,
    request_market_update,
)
from common.redis_protocol.market_update_api_helpers import MarketSignal, parse_int


class TestComputeDirection:
    """Tests for compute_direction function."""

    def test_buy_signal_when_kalshi_ask_below_theoretical(self):
        result = compute_direction(t_bid=None, t_ask=92, kalshi_bid=1, kalshi_ask=11)
        assert result == "BUY"

    def test_sell_signal_when_kalshi_bid_above_theoretical(self):
        result = compute_direction(t_bid=10, t_ask=None, kalshi_bid=15, kalshi_ask=20)
        assert result == "SELL"

    def test_none_when_both_conditions_true(self):
        result = compute_direction(t_bid=5, t_ask=95, kalshi_bid=10, kalshi_ask=90)
        assert result == "NONE"

    def test_none_when_neither_condition_true(self):
        result = compute_direction(t_bid=10, t_ask=50, kalshi_bid=5, kalshi_ask=55)
        assert result == "NONE"

    def test_none_when_no_theoretical_prices(self):
        result = compute_direction(t_bid=None, t_ask=None, kalshi_bid=10, kalshi_ask=20)
        assert result == "NONE"

    def test_none_when_kalshi_ask_is_zero(self):
        result = compute_direction(t_bid=None, t_ask=50, kalshi_bid=0, kalshi_ask=0)
        assert result == "NONE"


class TestRequestMarketUpdate:
    """Tests for request_market_update function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.hget = AsyncMock(return_value=None)
        redis.hset = AsyncMock()
        redis.hdel = AsyncMock()
        redis.publish = AsyncMock()
        redis.xadd = AsyncMock(return_value=b"1-0")
        return redis

    @pytest.mark.asyncio
    async def test_no_prices_provided_returns_no_success(self, mock_redis):
        result = await request_market_update(mock_redis, "market:key", "weather", None, None)

        assert result.success is False
        assert result.rejected is False
        assert result.reason == "no_prices_provided"

    @pytest.mark.asyncio
    async def test_update_succeeds(self, mock_redis):
        result = await request_market_update(mock_redis, "market:key", "weather", 50.0, 55.0)

        assert result.success is True
        assert result.rejected is False
        assert result.owning_algo is None  # Tracker sets ownership, not algos
        mock_redis.hset.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_with_only_bid_deletes_ask(self, mock_redis):
        result = await request_market_update(mock_redis, "market:key", "peak", 50.0, None)

        assert result.success is True
        mock_redis.hset.assert_called_once()
        mock_redis.hdel.assert_called_once_with("market:key", "peak:t_ask")

    @pytest.mark.asyncio
    async def test_update_with_only_ask_deletes_bid(self, mock_redis):
        result = await request_market_update(mock_redis, "market:key", "edge", None, 55.0)

        assert result.success is True
        mock_redis.hset.assert_called_once()
        mock_redis.hdel.assert_called_once_with("market:key", "edge:t_bid")

    @pytest.mark.asyncio
    async def test_update_with_both_prices_keeps_both(self, mock_redis):
        result = await request_market_update(mock_redis, "market:key", "pdf", 50.0, 55.0)

        assert result.success is True
        mock_redis.hset.assert_called_once()
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
    async def test_publishes_market_event_update_when_event_ticker_exists(self, mock_redis):
        def hget_side_effect(key, field):
            if field == "event_ticker":
                return b"KXHIGH-KDCA-20250101"
            return None

        mock_redis.hget = AsyncMock(side_effect=hget_side_effect)

        result = await request_market_update(mock_redis, "market:key", "weather", 50.0, 55.0)

        assert result.success is True
        # Both market event and algo signal go via stream_publish (xadd)
        _EXPECTED_XADD_CALLS_WITH_EVENT_TICKER = 2  # one for market event stream, one for algo signal stream
        assert mock_redis.xadd.call_count == _EXPECTED_XADD_CALLS_WITH_EVENT_TICKER

    @pytest.mark.asyncio
    async def test_publishes_algo_signal_when_no_event_ticker(self, mock_redis):
        result = await request_market_update(mock_redis, "market:key", "weather", 50.0, 55.0)

        assert result.success is True
        # No event_ticker means only the algo signal xadd (no market event xadd)
        mock_redis.xadd.assert_called_once()

    @pytest.mark.asyncio
    async def test_algo_signal_payload_format(self, mock_redis):
        import json

        from common.redis_protocol.streams.constants import ALGO_SIGNAL_STREAM

        result = await request_market_update(mock_redis, "market:key", "weather", 50.0, 55.0, ticker="TICKER1")

        assert result.success is True
        mock_redis.xadd.assert_called_once()
        call_args = mock_redis.xadd.call_args
        assert call_args[0][0] == ALGO_SIGNAL_STREAM
        fields = call_args[0][1]
        assert fields["ticker"] == "TICKER1"
        assert fields["algorithm"] == "weather"
        payload = json.loads(fields["payload"])
        assert payload["ticker"] == "TICKER1"
        assert payload["algorithm"] == "weather"
        assert payload["t_bid"] == 50.0
        assert payload["t_ask"] == 55.0


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


class TestParseInt:
    """Tests for parse_int helper function."""

    def test_none_returns_zero(self):
        assert parse_int(None) == 0

    def test_empty_string_returns_zero(self):
        assert parse_int("") == 0

    def test_empty_bytes_returns_zero(self):
        assert parse_int(b"") == 0

    def test_bytes_value(self):
        assert parse_int(b"42") == 42

    def test_string_value(self):
        assert parse_int("42") == 42

    def test_float_string_value(self):
        assert parse_int("42.5") == 42

    def test_invalid_type_raises_error(self):
        with pytest.raises(TypeError, match="Cannot parse float to int"):
            parse_int(42.5)


class TestBatchUpdateMarketSignals:
    """Tests for batch_update_market_signals function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.hget = AsyncMock(return_value=None)
        redis.pipeline = MagicMock()
        pipe = MagicMock()
        pipe.hset = MagicMock()
        pipe.hdel = MagicMock()
        pipe.execute = AsyncMock(return_value=[])
        redis.pipeline.return_value = pipe
        redis.publish = AsyncMock()
        redis.xadd = AsyncMock(return_value=b"1-0")
        return redis

    @pytest.fixture
    def mock_key_builder(self):
        return lambda ticker: f"markets:kalshi:test:{ticker}"

    @pytest.mark.asyncio
    async def test_empty_signals_returns_empty_result(self, mock_redis, mock_key_builder):
        result = await batch_update_market_signals(mock_redis, {}, "weather", mock_key_builder)
        assert result.succeeded == []
        assert result.rejected == []
        assert result.failed == []

    @pytest.mark.asyncio
    async def test_successful_batch_update(self, mock_redis, mock_key_builder):
        pipe = MagicMock()
        pipe.hset = MagicMock()
        pipe.hdel = MagicMock()
        pipe.execute = AsyncMock(return_value=[])
        mock_redis.pipeline.return_value = pipe

        result = await batch_update_market_signals(
            mock_redis,
            {"TEST1": {"t_bid": 50.0}, "TEST2": {"t_ask": 55.0}},
            "weather",
            mock_key_builder,
        )
        assert "TEST1" in result.succeeded
        assert "TEST2" in result.succeeded
        assert pipe.hset.call_count == 2


class TestExecuteBatchTransaction:
    """Tests for _execute_batch_transaction helper function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.hget = AsyncMock(return_value=b"EVENT123")
        redis.publish = AsyncMock()
        redis.xadd = AsyncMock(return_value=b"1-0")
        return redis

    @pytest.fixture
    def mock_pipe(self):
        pipe = MagicMock()
        pipe.execute = AsyncMock(return_value=[])
        return pipe

    @pytest.fixture
    def sample_signals(self):
        return [
            MarketSignal(
                ticker="TEST1",
                market_key="markets:kalshi:test:TEST1",
                t_bid=50.0,
                t_ask=None,
                algo="weather",
            ),
            MarketSignal(
                ticker="TEST2",
                market_key="markets:kalshi:test:TEST2",
                t_bid=None,
                t_ask=55.0,
                algo="weather",
            ),
        ]

    @pytest.mark.asyncio
    async def test_successful_execution(self, mock_redis, mock_pipe, sample_signals):
        result = await _execute_batch_transaction(mock_redis, mock_pipe, sample_signals, [], [], "weather")
        assert result.succeeded == ["TEST1", "TEST2"]
        assert result.rejected == []
        assert result.failed == []

    @pytest.mark.asyncio
    async def test_execution_failure_raises(self, mock_redis, mock_pipe, sample_signals):
        mock_pipe.execute = AsyncMock(side_effect=RuntimeError("Redis connection failed"))
        with pytest.raises(RuntimeError):
            await _execute_batch_transaction(mock_redis, mock_pipe, sample_signals, [], [], "weather")

    @pytest.mark.asyncio
    async def test_publish_failure_is_silent(self, mock_redis, mock_pipe, sample_signals):
        mock_redis.xadd = AsyncMock(side_effect=ConnectionError("publish failed"))
        result = await _execute_batch_transaction(mock_redis, mock_pipe, sample_signals, [], [], "weather")
        assert result.succeeded == ["TEST1", "TEST2"]


class TestPublishMarketEventUpdate:
    """Tests for publish_market_event_update exception handling."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.hget = AsyncMock()
        redis.hset = AsyncMock()
        redis.publish = AsyncMock()
        redis.hdel = AsyncMock()
        redis.xadd = AsyncMock(return_value=b"1-0")
        return redis

    @pytest.mark.asyncio
    async def test_publish_exception_is_raised(self, mock_redis):
        from common.redis_protocol.retry import RedisRetryError

        def hget_side_effect(key, field):
            if field == "event_ticker":
                return b"EVENT123"
            return None

        mock_redis.hget = AsyncMock(side_effect=hget_side_effect)
        mock_redis.xadd = AsyncMock(side_effect=RuntimeError("publish failed"))

        with pytest.raises(RedisRetryError, match="failed after 3 attempt"):
            await request_market_update(mock_redis, "market:key", "weather", 50.0, 55.0)


class TestBatchUpdateResult:
    """Tests for BatchUpdateResult dataclass."""

    def test_create_result(self):
        result = BatchUpdateResult(succeeded=["A", "B"], rejected=["C"], failed=["D"])
        assert result.succeeded == ["A", "B"]
        assert result.rejected == ["C"]
        assert result.failed == ["D"]


class TestBatchUpdateMarketSignalsAllFailed:
    """Additional tests for batch_update_market_signals edge cases."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.hget = AsyncMock(return_value=None)
        redis.pipeline = MagicMock()
        pipe = MagicMock()
        pipe.hset = MagicMock()
        pipe.hdel = MagicMock()
        pipe.execute = AsyncMock(return_value=[])
        redis.pipeline.return_value = pipe
        redis.publish = AsyncMock()
        redis.xadd = AsyncMock(return_value=b"1-0")
        return redis

    @pytest.fixture
    def mock_key_builder(self):
        return lambda ticker: f"markets:kalshi:test:{ticker}"

    @pytest.mark.asyncio
    async def test_all_signals_no_prices_returns_all_failed(self, mock_redis, mock_key_builder):
        """Test that when all signals have no prices, they all go to failed list."""
        result = await batch_update_market_signals(
            mock_redis,
            {"TEST1": {}, "TEST2": {"t_bid": None, "t_ask": None}},
            "weather",
            mock_key_builder,
        )
        assert result.succeeded == []
        assert result.rejected == []
        assert "TEST1" in result.failed
        assert "TEST2" in result.failed


class TestUpdateAndClearStale:
    """Tests for update_and_clear_stale function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.hget = AsyncMock(return_value=None)
        redis.hset = AsyncMock()
        redis.scan = AsyncMock(return_value=(0, []))
        redis.hdel = AsyncMock()
        redis.publish = AsyncMock()
        redis.xadd = AsyncMock(return_value=b"1-0")
        return redis

    @pytest.fixture
    def mock_key_builder(self):
        return lambda ticker: f"markets:kalshi:test:{ticker}"

    @pytest.mark.asyncio
    async def test_successful_update(self, mock_redis, mock_key_builder):
        from common.redis_protocol.market_update_api import update_and_clear_stale

        result = await update_and_clear_stale(
            mock_redis,
            {"TEST1": {"t_bid": 50.0}, "TEST2": {"t_ask": 55.0}},
            "weather",
            mock_key_builder,
            "markets:kalshi:*",
        )

        assert "TEST1" in result.succeeded
        assert "TEST2" in result.succeeded
        assert result.failed == []
        assert result.stale_cleared == []

    @pytest.mark.asyncio
    async def test_signals_with_no_prices_fail(self, mock_redis, mock_key_builder):
        from common.redis_protocol.market_update_api import update_and_clear_stale

        result = await update_and_clear_stale(
            mock_redis,
            {"TEST1": {"t_bid": 50.0}, "TEST2": {}},
            "weather",
            mock_key_builder,
            "markets:kalshi:*",
        )

        assert "TEST1" in result.succeeded
        assert "TEST2" in result.failed

    @pytest.mark.asyncio
    async def test_clears_stale_markets(self, mock_redis, mock_key_builder):
        from common.redis_protocol.market_update_api import update_and_clear_stale

        mock_redis.scan = AsyncMock(return_value=(0, [b"markets:kalshi:test:STALE"]))
        mock_redis.hget = AsyncMock(return_value=b"weather")

        result = await update_and_clear_stale(
            mock_redis,
            {"TEST1": {"t_bid": 50.0}},
            "weather",
            mock_key_builder,
            "markets:kalshi:*",
        )

        assert "TEST1" in result.succeeded
        assert "STALE" in result.stale_cleared

    @pytest.mark.asyncio
    async def test_write_failure_raises(self, mock_redis, mock_key_builder):
        from common.redis_protocol.market_update_api import update_and_clear_stale

        mock_redis.hset = AsyncMock(side_effect=RuntimeError("write failed"))

        with pytest.raises(RuntimeError):
            await update_and_clear_stale(
                mock_redis,
                {"TEST1": {"t_bid": 50.0}},
                "weather",
                mock_key_builder,
                "markets:kalshi:*",
            )


class TestAlgoUpdateResult:
    """Tests for AlgoUpdateResult dataclass."""

    def test_create_result(self):
        from common.redis_protocol.market_update_api import AlgoUpdateResult

        result = AlgoUpdateResult(succeeded=["A", "B"], failed=["C"], stale_cleared=["D"])
        assert result.succeeded == ["A", "B"]
        assert result.failed == ["C"]
        assert result.stale_cleared == ["D"]
