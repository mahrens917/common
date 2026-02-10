"""Tests for consumer group management."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.redis_protocol.retry import RedisRetryError
from common.redis_protocol.streams.consumer_group import (
    claim_pending_entries,
    ensure_consumer_group,
)


class TestEnsureConsumerGroup:
    """Tests for ensure_consumer_group function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.xgroup_create = AsyncMock(return_value=True)
        return redis

    @pytest.mark.asyncio
    async def test_creates_group_with_mkstream(self, mock_redis):
        await ensure_consumer_group(mock_redis, "stream:test", "my-group")

        mock_redis.xgroup_create.assert_called_once_with("stream:test", "my-group", id="0", mkstream=True)

    @pytest.mark.asyncio
    async def test_handles_busygroup_error(self, mock_redis):
        mock_redis.xgroup_create = AsyncMock(side_effect=Exception("BUSYGROUP Consumer Group name already exists"))

        # Should not raise
        await ensure_consumer_group(mock_redis, "stream:test", "my-group")

    @pytest.mark.asyncio
    async def test_raises_non_busygroup_errors(self, mock_redis):
        mock_redis.xgroup_create = AsyncMock(side_effect=ConnectionError("connection lost"))

        with pytest.raises(ConnectionError):
            await ensure_consumer_group(mock_redis, "stream:test", "my-group")

    @pytest.mark.asyncio
    async def test_handles_busygroup_wrapped_in_retry_error(self, mock_redis):
        """BUSYGROUP wrapped in RedisRetryError by RetryRedisClient is still handled."""
        cause = Exception("BUSYGROUP Consumer Group name already exists")
        wrapped = RedisRetryError("xgroup_create failed after 3 attempt(s)")
        wrapped.__cause__ = cause
        mock_redis.xgroup_create = AsyncMock(side_effect=wrapped)

        # Should not raise
        await ensure_consumer_group(mock_redis, "stream:test", "my-group")

    @pytest.mark.asyncio
    async def test_custom_start_id(self, mock_redis):
        await ensure_consumer_group(mock_redis, "stream:test", "my-group", start_id="$")

        call_args = mock_redis.xgroup_create.call_args
        assert call_args[1]["id"] == "$"


class TestClaimPendingEntries:
    """Tests for claim_pending_entries function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.xautoclaim = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_returns_claimed_entries(self, mock_redis):
        mock_redis.xautoclaim = AsyncMock(
            return_value=(
                b"0-0",
                [
                    (b"1234-0", {b"ticker": b"AAPL", b"price": b"150"}),
                    (b"1234-1", {b"ticker": b"GOOG", b"price": b"2800"}),
                ],
                [],
            )
        )

        result = await claim_pending_entries(mock_redis, "stream:test", "group", "consumer")

        assert len(result) == 2
        assert result[0] == ("1234-0", {"ticker": "AAPL", "price": "150"})
        assert result[1] == ("1234-1", {"ticker": "GOOG", "price": "2800"})

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_pending(self, mock_redis):
        mock_redis.xautoclaim = AsyncMock(return_value=(b"0-0", [], []))

        result = await claim_pending_entries(mock_redis, "stream:test", "group", "consumer")

        assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_for_none_result(self, mock_redis):
        mock_redis.xautoclaim = AsyncMock(return_value=None)

        result = await claim_pending_entries(mock_redis, "stream:test", "group", "consumer")

        assert result == []

    @pytest.mark.asyncio
    async def test_decodes_string_entry_ids(self, mock_redis):
        mock_redis.xautoclaim = AsyncMock(
            return_value=(
                "0-0",
                [("1234-0", {"ticker": "AAPL"})],
                [],
            )
        )

        result = await claim_pending_entries(mock_redis, "stream:test", "group", "consumer")

        assert result[0][0] == "1234-0"
        assert result[0][1] == {"ticker": "AAPL"}
