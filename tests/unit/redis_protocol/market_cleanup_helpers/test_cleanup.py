"""Tests for market cleanup module."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.redis_protocol.market_cleanup_helpers.cleanup import (
    MIN_DERIBIT_KEY_PARTS,
    ExpiredMarketCleaner,
)


class TestExpiredMarketCleanerInit:
    """Tests for ExpiredMarketCleaner initialization."""

    def test_init_stores_redis_client(self) -> None:
        """Stores redis_client."""
        mock_redis = MagicMock()

        cleaner = ExpiredMarketCleaner(mock_redis)

        assert cleaner._redis is mock_redis

    def test_init_default_grace_period(self) -> None:
        """Sets default grace_period_days to 0."""
        mock_redis = MagicMock()

        cleaner = ExpiredMarketCleaner(mock_redis)

        assert cleaner._grace_period_days == 0

    def test_init_custom_grace_period(self) -> None:
        """Sets custom grace_period_days."""
        mock_redis = MagicMock()

        cleaner = ExpiredMarketCleaner(mock_redis, grace_period_days=7)

        assert cleaner._grace_period_days == 7


class TestCleanupKalshiMarkets:
    """Tests for ExpiredMarketCleaner.cleanup_kalshi_markets method."""

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_keys(self) -> None:
        """Returns 0 when no keys match pattern."""
        mock_redis = AsyncMock()
        mock_redis.scan = AsyncMock(return_value=(0, []))

        cleaner = ExpiredMarketCleaner(mock_redis)

        result = await cleaner.cleanup_kalshi_markets()

        assert result == 0
        mock_redis.scan.assert_called_once()

    @pytest.mark.asyncio
    async def test_processes_all_pages(self) -> None:
        """Processes all scan pages until cursor returns to 0."""
        mock_redis = AsyncMock()
        mock_redis.scan = AsyncMock(
            side_effect=[
                (123, [b"markets:kalshi:test:TICKER1"]),
                (0, [b"markets:kalshi:test:TICKER2"]),
            ]
        )
        mock_redis.hgetall = AsyncMock(return_value={})
        mock_redis.delete = AsyncMock()

        cleaner = ExpiredMarketCleaner(mock_redis)

        await cleaner.cleanup_kalshi_markets()

        assert mock_redis.scan.call_count == 2

    @pytest.mark.asyncio
    async def test_deletes_expired_markets(self) -> None:
        """Deletes expired markets."""
        mock_redis = AsyncMock()
        mock_redis.scan = AsyncMock(return_value=(0, [b"markets:kalshi:test:TICKER1"]))

        # Make a market that expired 10 days ago
        old_expiration = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        mock_redis.hgetall = AsyncMock(return_value={b"latest_expiration_time": old_expiration.encode()})
        mock_redis.delete = AsyncMock()

        cleaner = ExpiredMarketCleaner(mock_redis, grace_period_days=1)

        result = await cleaner.cleanup_kalshi_markets()

        assert result == 1
        mock_redis.delete.assert_called_once_with("markets:kalshi:test:TICKER1")

    @pytest.mark.asyncio
    async def test_does_not_delete_non_expired_markets(self) -> None:
        """Does not delete markets not yet expired."""
        mock_redis = AsyncMock()
        mock_redis.scan = AsyncMock(return_value=(0, [b"markets:kalshi:test:TICKER1"]))

        # Make a market that expires in the future
        future_expiration = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
        mock_redis.hgetall = AsyncMock(return_value={b"latest_expiration_time": future_expiration.encode()})
        mock_redis.delete = AsyncMock()

        cleaner = ExpiredMarketCleaner(mock_redis, grace_period_days=1)

        result = await cleaner.cleanup_kalshi_markets()

        assert result == 0
        mock_redis.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_logs_info_when_markets_deleted(self) -> None:
        """Logs info message when markets are deleted."""
        mock_redis = AsyncMock()
        mock_redis.scan = AsyncMock(return_value=(0, [b"markets:kalshi:test:TICKER1"]))

        old_expiration = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        mock_redis.hgetall = AsyncMock(return_value={b"latest_expiration_time": old_expiration.encode()})
        mock_redis.delete = AsyncMock()

        cleaner = ExpiredMarketCleaner(mock_redis, grace_period_days=1)

        with patch("common.redis_protocol.market_cleanup_helpers.cleanup.logger") as mock_logger:
            await cleaner.cleanup_kalshi_markets()

        mock_logger.info.assert_called_once()
        assert "Cleaned up" in mock_logger.info.call_args[0][0]


class TestProcessKalshiMarketKey:
    """Tests for ExpiredMarketCleaner._process_kalshi_market_key method."""

    @pytest.mark.asyncio
    async def test_returns_false_when_no_market_data(self) -> None:
        """Returns False when market has no data."""
        mock_redis = AsyncMock()
        mock_redis.hgetall = AsyncMock(return_value={})

        cleaner = ExpiredMarketCleaner(mock_redis)

        result = await cleaner._process_kalshi_market_key(b"markets:kalshi:test:TICKER1")

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_no_expiration_time(self) -> None:
        """Returns False when market has no expiration time."""
        mock_redis = AsyncMock()
        mock_redis.hgetall = AsyncMock(return_value={b"some_field": b"some_value"})

        cleaner = ExpiredMarketCleaner(mock_redis)

        result = await cleaner._process_kalshi_market_key(b"markets:kalshi:test:TICKER1")

        assert result is False

    @pytest.mark.asyncio
    async def test_handles_string_key(self) -> None:
        """Handles string key (not bytes)."""
        mock_redis = AsyncMock()
        mock_redis.hgetall = AsyncMock(return_value={})

        cleaner = ExpiredMarketCleaner(mock_redis)

        result = await cleaner._process_kalshi_market_key("markets:kalshi:test:TICKER1")

        assert result is False
        mock_redis.hgetall.assert_called_once_with("markets:kalshi:test:TICKER1")

    @pytest.mark.asyncio
    async def test_deletes_expired_market_and_returns_true(self) -> None:
        """Deletes expired market and returns True."""
        mock_redis = AsyncMock()
        old_expiration = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        mock_redis.hgetall = AsyncMock(return_value={b"latest_expiration_time": old_expiration.encode()})
        mock_redis.delete = AsyncMock()

        cleaner = ExpiredMarketCleaner(mock_redis, grace_period_days=1)

        with patch("common.redis_protocol.market_cleanup_helpers.cleanup.logger"):
            result = await cleaner._process_kalshi_market_key(b"markets:kalshi:test:TICKER1")

        assert result is True
        mock_redis.delete.assert_called_once()


class TestCleanupDeribitOptions:
    """Tests for ExpiredMarketCleaner.cleanup_deribit_options method."""

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_keys(self) -> None:
        """Returns 0 when no keys match pattern."""
        mock_redis = AsyncMock()
        mock_redis.scan = AsyncMock(return_value=(0, []))

        cleaner = ExpiredMarketCleaner(mock_redis)

        result = await cleaner.cleanup_deribit_options()

        assert result == 0

    @pytest.mark.asyncio
    async def test_skips_keys_with_insufficient_parts(self) -> None:
        """Skips keys with fewer than MIN_DERIBIT_KEY_PARTS parts."""
        mock_redis = AsyncMock()
        # Key with only 4 parts (below minimum of 5)
        mock_redis.scan = AsyncMock(return_value=(0, [b"markets:deribit:option:BTC"]))
        mock_redis.delete = AsyncMock()

        cleaner = ExpiredMarketCleaner(mock_redis)

        result = await cleaner.cleanup_deribit_options()

        assert result == 0
        mock_redis.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_deletes_expired_options(self) -> None:
        """Deletes expired Deribit options."""
        mock_redis = AsyncMock()
        # Key with expired date
        old_date = (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%d")
        key = f"markets:deribit:option:BTC:{old_date}:50000:C".encode()
        mock_redis.scan = AsyncMock(return_value=(0, [key]))
        mock_redis.delete = AsyncMock()

        cleaner = ExpiredMarketCleaner(mock_redis, grace_period_days=1)

        with patch("common.redis_protocol.market_cleanup_helpers.cleanup.logger"):
            result = await cleaner.cleanup_deribit_options()

        assert result == 1
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_does_not_delete_non_expired_options(self) -> None:
        """Does not delete options not yet expired."""
        mock_redis = AsyncMock()
        # Key with future date
        future_date = (datetime.now(timezone.utc) + timedelta(days=10)).strftime("%Y-%m-%d")
        key = f"markets:deribit:option:BTC:{future_date}:50000:C".encode()
        mock_redis.scan = AsyncMock(return_value=(0, [key]))
        mock_redis.delete = AsyncMock()

        cleaner = ExpiredMarketCleaner(mock_redis, grace_period_days=1)

        result = await cleaner.cleanup_deribit_options()

        assert result == 0
        mock_redis.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_string_keys(self) -> None:
        """Handles string keys (not bytes)."""
        mock_redis = AsyncMock()
        old_date = (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%d")
        key = f"markets:deribit:option:BTC:{old_date}:50000:C"
        mock_redis.scan = AsyncMock(return_value=(0, [key]))
        mock_redis.delete = AsyncMock()

        cleaner = ExpiredMarketCleaner(mock_redis, grace_period_days=1)

        with patch("common.redis_protocol.market_cleanup_helpers.cleanup.logger"):
            result = await cleaner.cleanup_deribit_options()

        assert result == 1

    @pytest.mark.asyncio
    async def test_logs_info_when_options_deleted(self) -> None:
        """Logs info message when options are deleted."""
        mock_redis = AsyncMock()
        old_date = (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%d")
        key = f"markets:deribit:option:BTC:{old_date}:50000:C".encode()
        mock_redis.scan = AsyncMock(return_value=(0, [key]))
        mock_redis.delete = AsyncMock()

        cleaner = ExpiredMarketCleaner(mock_redis, grace_period_days=1)

        with patch("common.redis_protocol.market_cleanup_helpers.cleanup.logger") as mock_logger:
            await cleaner.cleanup_deribit_options()

        mock_logger.info.assert_called_once()
        assert "Cleaned up" in mock_logger.info.call_args[0][0]

    @pytest.mark.asyncio
    async def test_processes_multiple_pages(self) -> None:
        """Processes all scan pages."""
        mock_redis = AsyncMock()
        old_date = (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%d")
        key1 = f"markets:deribit:option:BTC:{old_date}:50000:C".encode()
        key2 = f"markets:deribit:option:BTC:{old_date}:60000:P".encode()

        mock_redis.scan = AsyncMock(
            side_effect=[
                (123, [key1]),
                (0, [key2]),
            ]
        )
        mock_redis.delete = AsyncMock()

        cleaner = ExpiredMarketCleaner(mock_redis, grace_period_days=1)

        with patch("common.redis_protocol.market_cleanup_helpers.cleanup.logger"):
            result = await cleaner.cleanup_deribit_options()

        assert result == 2
        assert mock_redis.scan.call_count == 2


class TestCleanupDeribitFutures:
    """Tests for ExpiredMarketCleaner.cleanup_deribit_futures method."""

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_keys(self) -> None:
        """Returns 0 when no keys match pattern."""
        mock_redis = AsyncMock()
        mock_redis.scan = AsyncMock(return_value=(0, []))

        cleaner = ExpiredMarketCleaner(mock_redis)

        result = await cleaner.cleanup_deribit_futures()

        assert result == 0

    @pytest.mark.asyncio
    async def test_skips_keys_with_insufficient_parts(self) -> None:
        """Skips keys with fewer than MIN_DERIBIT_KEY_PARTS parts."""
        mock_redis = AsyncMock()
        mock_redis.scan = AsyncMock(return_value=(0, [b"markets:deribit:future:BTC"]))
        mock_redis.delete = AsyncMock()

        cleaner = ExpiredMarketCleaner(mock_redis)

        result = await cleaner.cleanup_deribit_futures()

        assert result == 0
        mock_redis.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_deletes_expired_futures(self) -> None:
        """Deletes expired Deribit futures."""
        mock_redis = AsyncMock()
        old_date = (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%d")
        key = f"markets:deribit:future:BTC:{old_date}".encode()
        mock_redis.scan = AsyncMock(return_value=(0, [key]))
        mock_redis.delete = AsyncMock()

        cleaner = ExpiredMarketCleaner(mock_redis, grace_period_days=1)

        with patch("common.redis_protocol.market_cleanup_helpers.cleanup.logger"):
            result = await cleaner.cleanup_deribit_futures()

        assert result == 1
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_does_not_delete_non_expired_futures(self) -> None:
        """Does not delete futures not yet expired."""
        mock_redis = AsyncMock()
        future_date = (datetime.now(timezone.utc) + timedelta(days=10)).strftime("%Y-%m-%d")
        key = f"markets:deribit:future:BTC:{future_date}".encode()
        mock_redis.scan = AsyncMock(return_value=(0, [key]))
        mock_redis.delete = AsyncMock()

        cleaner = ExpiredMarketCleaner(mock_redis, grace_period_days=1)

        result = await cleaner.cleanup_deribit_futures()

        assert result == 0
        mock_redis.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_perpetual_futures(self) -> None:
        """Skips perpetual futures (they never expire)."""
        mock_redis = AsyncMock()
        key = b"markets:deribit:future:BTC:perpetual"
        mock_redis.scan = AsyncMock(return_value=(0, [key]))
        mock_redis.delete = AsyncMock()

        cleaner = ExpiredMarketCleaner(mock_redis, grace_period_days=1)

        result = await cleaner.cleanup_deribit_futures()

        assert result == 0
        mock_redis.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_perpetual_futures_case_insensitive(self) -> None:
        """Skips perpetual futures regardless of case."""
        mock_redis = AsyncMock()
        key = b"markets:deribit:future:BTC:PERPETUAL"
        mock_redis.scan = AsyncMock(return_value=(0, [key]))
        mock_redis.delete = AsyncMock()

        cleaner = ExpiredMarketCleaner(mock_redis, grace_period_days=1)

        result = await cleaner.cleanup_deribit_futures()

        assert result == 0
        mock_redis.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_logs_info_when_futures_deleted(self) -> None:
        """Logs info message when futures are deleted."""
        mock_redis = AsyncMock()
        old_date = (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%d")
        key = f"markets:deribit:future:BTC:{old_date}".encode()
        mock_redis.scan = AsyncMock(return_value=(0, [key]))
        mock_redis.delete = AsyncMock()

        cleaner = ExpiredMarketCleaner(mock_redis, grace_period_days=1)

        with patch("common.redis_protocol.market_cleanup_helpers.cleanup.logger") as mock_logger:
            await cleaner.cleanup_deribit_futures()

        mock_logger.info.assert_called_once()
        assert "Cleaned up" in mock_logger.info.call_args[0][0]


class TestMinDeribitKeyParts:
    """Tests for MIN_DERIBIT_KEY_PARTS constant."""

    def test_constant_value(self) -> None:
        """Verifies MIN_DERIBIT_KEY_PARTS is 5."""
        assert MIN_DERIBIT_KEY_PARTS == 5
