"""Tests for subscriber_helpers.reader module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.redis_protocol.streams.subscriber_helpers.reader import read_stream_entries


class TestReadStreamEntries:
    """Tests for read_stream_entries."""

    @pytest.mark.asyncio
    async def test_decodes_response(self):
        entry_id = b"1700000000000-0"
        fields = {b"ticker": b"AAPL", b"price": b"150"}
        redis_client = MagicMock()
        redis_client.xreadgroup = AsyncMock(return_value=[[b"stream:test", [(entry_id, fields)]]])

        result = await read_stream_entries(redis_client, "stream:test", "group", "consumer")

        assert len(result) == 1
        assert result[0][0] == "1700000000000-0"

    @pytest.mark.asyncio
    async def test_returns_empty_on_none(self):
        redis_client = MagicMock()
        redis_client.xreadgroup = AsyncMock(return_value=None)

        result = await read_stream_entries(redis_client, "stream:test", "group", "consumer")

        assert result == []

    @pytest.mark.asyncio
    async def test_passes_correct_args(self):
        redis_client = MagicMock()
        redis_client.xreadgroup = AsyncMock(return_value=None)

        await read_stream_entries(redis_client, "stream:test", "grp", "con", count=50, block_ms=1000)

        redis_client.xreadgroup.assert_called_once_with("grp", "con", {"stream:test": ">"}, count=50, block=1000)
