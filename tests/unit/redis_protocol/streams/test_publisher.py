"""Tests for stream publisher."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.redis_protocol.streams.constants import STREAM_DEFAULT_MAXLEN
from common.redis_protocol.streams.publisher import stream_publish


class TestStreamPublish:
    """Tests for stream_publish function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.xadd = AsyncMock(return_value=b"1234567890-0")
        return redis

    @pytest.mark.asyncio
    async def test_publishes_with_correct_args(self, mock_redis):
        await stream_publish(mock_redis, "stream:test", {"key": "value"})

        mock_redis.xadd.assert_called_once_with(
            "stream:test",
            {"key": "value"},
            maxlen=STREAM_DEFAULT_MAXLEN,
            approximate=True,
        )

    @pytest.mark.asyncio
    async def test_returns_entry_id_from_bytes(self, mock_redis):
        mock_redis.xadd = AsyncMock(return_value=b"1234567890-0")

        result = await stream_publish(mock_redis, "stream:test", {"k": "v"})

        assert result == "1234567890-0"

    @pytest.mark.asyncio
    async def test_returns_entry_id_from_string(self, mock_redis):
        mock_redis.xadd = AsyncMock(return_value="1234567890-0")

        result = await stream_publish(mock_redis, "stream:test", {"k": "v"})

        assert result == "1234567890-0"

    @pytest.mark.asyncio
    async def test_converts_values_to_strings(self, mock_redis):
        await stream_publish(mock_redis, "stream:test", {"count": 42, "price": 99.5})

        call_args = mock_redis.xadd.call_args
        fields = call_args[0][1]
        assert fields == {"count": "42", "price": "99.5"}

    @pytest.mark.asyncio
    async def test_custom_maxlen(self, mock_redis):
        custom_maxlen = STREAM_DEFAULT_MAXLEN * 2
        await stream_publish(mock_redis, "stream:test", {"k": "v"}, maxlen=custom_maxlen)

        call_args = mock_redis.xadd.call_args
        assert call_args[1]["maxlen"] == custom_maxlen
