"""Tests for subscriber_helpers.reader module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from common.redis_protocol.streams.subscriber import StreamConfig
from common.redis_protocol.streams.subscriber_helpers.reader import read_stream_entries, stream_read_loop


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


class TestStreamReadLoop:
    """Tests for stream_read_loop."""

    @pytest.fixture
    def config(self):
        return StreamConfig(
            stream_name="stream:test",
            group_name="test-group",
            consumer_name="test-consumer",
        )

    @pytest.mark.asyncio
    async def test_enqueues_entries(self, config):
        """Entries read from stream are put into the queue."""
        call_count = {"n": 0}

        async def mock_xreadgroup(_group, _consumer, _streams, count, block):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return [[b"stream:test", [(b"1-0", {b"ticker": b"AAPL"})]]]
            return None

        redis_client = MagicMock()
        redis_client.xreadgroup = AsyncMock(side_effect=mock_xreadgroup)
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)

        def is_running():
            return call_count["n"] < 3

        await stream_read_loop(is_running, redis_client, config, queue, "test")

        assert queue.qsize() == 1
        entry_id, identifier, fields = queue.get_nowait()
        assert entry_id == "1-0"
        assert identifier == "AAPL"

    @pytest.mark.asyncio
    async def test_continues_on_empty_response(self, config):
        """Loop continues when xreadgroup returns empty."""
        call_count = {"n": 0}

        redis_client = MagicMock()
        redis_client.xreadgroup = AsyncMock(return_value=None)
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)

        def is_running():
            call_count["n"] += 1
            return call_count["n"] <= 3

        await stream_read_loop(is_running, redis_client, config, queue, "test")

        assert queue.qsize() == 0

    @pytest.mark.asyncio
    async def test_recovers_from_read_error(self, config):
        """Loop retries after a transient read error."""
        call_count = {"n": 0}

        async def mock_xreadgroup(_group, _consumer, _streams, count, block):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise ConnectionError("transient")
            if call_count["n"] == 2:
                return [[b"stream:test", [(b"2-0", {b"ticker": b"MSFT"})]]]
            return None

        redis_client = MagicMock()
        redis_client.xreadgroup = AsyncMock(side_effect=mock_xreadgroup)
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)

        def is_running():
            return call_count["n"] < 4

        await stream_read_loop(is_running, redis_client, config, queue, "test")

        assert queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_uses_identifier_field(self, config):
        """Uses the configured identifier_field to extract the identifier."""
        config.identifier_field = "symbol"
        call_count = {"n": 0}

        async def mock_xreadgroup(_group, _consumer, _streams, count, block):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return [[b"stream:test", [(b"1-0", {b"symbol": b"GOOG"})]]]
            return None

        redis_client = MagicMock()
        redis_client.xreadgroup = AsyncMock(side_effect=mock_xreadgroup)
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)

        def is_running():
            return call_count["n"] < 3

        await stream_read_loop(is_running, redis_client, config, queue, "test")

        assert queue.qsize() == 1
        _, identifier, _ = queue.get_nowait()
        assert identifier == "GOOG"
