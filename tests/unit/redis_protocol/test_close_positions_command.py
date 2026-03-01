"""Tests for close_positions_command module."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.redis_protocol.close_positions_command import (
    CLOSE_POSITIONS_COMMAND_KEY,
    CLOSE_POSITIONS_RESULT_KEY,
    COMMAND_TTL_SECONDS,
    RESULT_TTL_SECONDS,
    ClosePositionsResult,
    clear_close_positions_command,
    clear_close_positions_result,
    get_close_positions_command,
    get_close_positions_result,
    request_close_all_positions,
    write_close_positions_result,
)


class TestConstants:
    """Tests for module constants."""

    def test_command_key_value(self):
        assert CLOSE_POSITIONS_COMMAND_KEY == "config:command:close_positions"

    def test_result_key_value(self):
        assert CLOSE_POSITIONS_RESULT_KEY == "config:command:close_positions:result"

    def test_result_ttl_seconds(self):
        assert RESULT_TTL_SECONDS == 30


class TestClosePositionsResult:
    """Tests for ClosePositionsResult dataclass."""

    def test_create_result(self):
        result = ClosePositionsResult(
            closed_count=5,
            total_count=10,
            timestamp="2024-01-15T12:00:00+00:00",
        )

        assert result.closed_count == 5
        assert result.total_count == 10
        assert result.timestamp == "2024-01-15T12:00:00+00:00"


class TestRequestCloseAllPositions:
    """Tests for request_close_all_positions function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.set = AsyncMock()
        redis.xadd = AsyncMock(return_value=b"1234-0")
        return redis

    @pytest.mark.asyncio
    async def test_sets_timestamp_to_redis(self, mock_redis):
        with patch("common.time_utils.get_current_utc") as mock_time:
            mock_time.return_value.isoformat.return_value = "2024-01-15T12:00:00+00:00"

            await request_close_all_positions(mock_redis)

            mock_redis.set.assert_called_once_with(CLOSE_POSITIONS_COMMAND_KEY, "2024-01-15T12:00:00+00:00", ex=COMMAND_TTL_SECONDS)

    @pytest.mark.asyncio
    async def test_publishes_to_stream(self, mock_redis):
        with patch("common.time_utils.get_current_utc") as mock_time:
            mock_time.return_value.isoformat.return_value = "2024-01-15T12:00:00+00:00"

            await request_close_all_positions(mock_redis)

            mock_redis.xadd.assert_called_once()
            call_args = mock_redis.xadd.call_args
            assert call_args[0][0] == "stream:close_positions"
            fields = call_args[0][1]
            assert fields["timestamp"] == "2024-01-15T12:00:00+00:00"
            assert fields["action"] == "close_all"


class TestGetClosePositionsCommand:
    """Tests for get_close_positions_command function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.get = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_returns_none_when_no_command(self, mock_redis):
        mock_redis.get = AsyncMock(return_value=None)

        result = await get_close_positions_command(mock_redis)

        assert result is None
        mock_redis.get.assert_called_once_with(CLOSE_POSITIONS_COMMAND_KEY)

    @pytest.mark.asyncio
    async def test_returns_timestamp_from_bytes(self, mock_redis):
        mock_redis.get = AsyncMock(return_value=b"2024-01-15T12:00:00+00:00")

        result = await get_close_positions_command(mock_redis)

        assert result == "2024-01-15T12:00:00+00:00"

    @pytest.mark.asyncio
    async def test_returns_timestamp_from_string(self, mock_redis):
        mock_redis.get = AsyncMock(return_value="2024-01-15T12:00:00+00:00")

        result = await get_close_positions_command(mock_redis)

        assert result == "2024-01-15T12:00:00+00:00"


class TestClearClosePositionsCommand:
    """Tests for clear_close_positions_command function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.delete = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_deletes_command_key(self, mock_redis):
        await clear_close_positions_command(mock_redis)

        mock_redis.delete.assert_called_once_with(CLOSE_POSITIONS_COMMAND_KEY)


class TestWriteClosePositionsResult:
    """Tests for write_close_positions_result function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.set = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_writes_result_to_redis(self, mock_redis):
        with patch("common.time_utils.get_current_utc") as mock_time:
            mock_time.return_value.isoformat.return_value = "2024-01-15T12:00:00+00:00"

            await write_close_positions_result(mock_redis, closed_count=5, total_count=10)

            expected_data = json.dumps(
                {
                    "closed_count": 5,
                    "total_count": 10,
                    "timestamp": "2024-01-15T12:00:00+00:00",
                }
            )
            mock_redis.set.assert_called_once_with(CLOSE_POSITIONS_RESULT_KEY, expected_data, ex=RESULT_TTL_SECONDS)


class TestGetClosePositionsResult:
    """Tests for get_close_positions_result function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.get = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_returns_none_when_no_result(self, mock_redis):
        mock_redis.get = AsyncMock(return_value=None)

        result = await get_close_positions_result(mock_redis)

        assert result is None
        mock_redis.get.assert_called_once_with(CLOSE_POSITIONS_RESULT_KEY)

    @pytest.mark.asyncio
    async def test_returns_result_from_bytes(self, mock_redis):
        data = json.dumps(
            {
                "closed_count": 5,
                "total_count": 10,
                "timestamp": "2024-01-15T12:00:00+00:00",
            }
        )
        mock_redis.get = AsyncMock(return_value=data.encode("utf-8"))

        result = await get_close_positions_result(mock_redis)

        assert result is not None
        assert result.closed_count == 5
        assert result.total_count == 10
        assert result.timestamp == "2024-01-15T12:00:00+00:00"

    @pytest.mark.asyncio
    async def test_returns_result_from_string(self, mock_redis):
        data = json.dumps(
            {
                "closed_count": 3,
                "total_count": 7,
                "timestamp": "2024-01-15T14:00:00+00:00",
            }
        )
        mock_redis.get = AsyncMock(return_value=data)

        result = await get_close_positions_result(mock_redis)

        assert result is not None
        assert result.closed_count == 3
        assert result.total_count == 7
        assert result.timestamp == "2024-01-15T14:00:00+00:00"


class TestClearClosePositionsResult:
    """Tests for clear_close_positions_result function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.delete = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_deletes_result_key(self, mock_redis):
        await clear_close_positions_result(mock_redis)

        mock_redis.delete.assert_called_once_with(CLOSE_POSITIONS_RESULT_KEY)
