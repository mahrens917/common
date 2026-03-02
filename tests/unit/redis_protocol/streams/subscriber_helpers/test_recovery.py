"""Tests for subscriber_helpers.recovery module."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from common.redis_protocol.streams.subscriber import StreamConfig
from common.redis_protocol.streams.subscriber_helpers.recovery import (
    initialize_consumer_group,
    parse_entry_timestamp_ms,
    recover_and_filter_pending,
    recover_pending_entries,
)


class TestInitializeConsumerGroup:
    """Tests for initialize_consumer_group."""

    @pytest.mark.asyncio
    async def test_creates_group(self):
        redis_client = MagicMock()
        redis_client.xgroup_create = AsyncMock(return_value=True)
        await initialize_consumer_group(redis_client, "stream:test", "group")
        redis_client.xgroup_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_busygroup(self):
        from redis.exceptions import ResponseError

        redis_client = MagicMock()
        redis_client.xgroup_create = AsyncMock(side_effect=ResponseError("BUSYGROUP"))
        await initialize_consumer_group(redis_client, "stream:test", "group")

    @pytest.mark.asyncio
    async def test_reraises_non_busygroup(self):
        from redis.exceptions import ResponseError

        redis_client = MagicMock()
        redis_client.xgroup_create = AsyncMock(side_effect=ResponseError("OTHER"))
        with pytest.raises(ResponseError, match="OTHER"):
            await initialize_consumer_group(redis_client, "stream:test", "group")


class TestRecoverPendingEntries:
    """Tests for recover_pending_entries."""

    @pytest.mark.asyncio
    async def test_returns_claimed_entries(self):
        redis_client = MagicMock()
        entry_id = b"1700000000000-0"
        fields = {b"ticker": b"AAPL"}
        redis_client.xautoclaim = AsyncMock(return_value=(b"0-0", [(entry_id, fields)], []))

        result = await recover_pending_entries(redis_client, "stream:test", "group", "consumer")

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_pending(self):
        redis_client = MagicMock()
        redis_client.xautoclaim = AsyncMock(return_value=(b"0-0", [], []))

        result = await recover_pending_entries(redis_client, "stream:test", "group", "consumer")

        assert result == []


class TestParseEntryTimestampMs:
    """Tests for parse_entry_timestamp_ms."""

    def test_valid_entry_id(self):
        assert parse_entry_timestamp_ms("1700000000000-0") == 1700000000000

    def test_no_dash(self):
        assert parse_entry_timestamp_ms("nodash") == 0

    def test_dash_at_start(self):
        assert parse_entry_timestamp_ms("-123") == 0

    def test_non_numeric_prefix(self):
        assert parse_entry_timestamp_ms("abc-0") == 0

    def test_empty_string(self):
        assert parse_entry_timestamp_ms("") == 0


class TestRecoverAndFilterPending:
    """Tests for recover_and_filter_pending."""

    @pytest.mark.asyncio
    async def test_enqueues_pending_entries(self):
        ts = str(int(time.time() * 1000))
        entry_id = f"{ts}-0"
        pending = [(entry_id, {"ticker": "AAPL"})]
        redis_client = MagicMock()
        redis_client.xack = AsyncMock()
        config = StreamConfig(stream_name="s", group_name="g", consumer_name="c")
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)

        await recover_and_filter_pending(pending, redis_client, config, queue, "test")

        assert queue.qsize() == 1
        item = queue.get_nowait()
        assert item[0] == entry_id

    @pytest.mark.asyncio
    async def test_old_pending_entry_still_enqueued(self):
        entry_id = "1000000000-0"
        pending = [(entry_id, {"ticker": "OLD"})]
        redis_client = MagicMock()
        redis_client.xack = AsyncMock()
        config = StreamConfig(stream_name="s", group_name="g", consumer_name="c")
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)

        await recover_and_filter_pending(pending, redis_client, config, queue, "test")

        assert queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_queue_full_skips_overflow(self):
        ts = str(int(time.time() * 1000))
        entry_id = f"{ts}-0"
        pending = [(entry_id, {"ticker": "AAPL"})]
        redis_client = MagicMock()
        redis_client.xack = AsyncMock()
        config = StreamConfig(stream_name="s", group_name="g", consumer_name="c")
        queue: asyncio.Queue = asyncio.Queue(maxsize=1)
        queue.put_nowait(("existing", "X", {}))

        await recover_and_filter_pending(pending, redis_client, config, queue, "test")

        redis_client.xack.assert_not_called()

    @pytest.mark.asyncio
    async def test_unparseable_entry_id(self):
        pending = [("bad-id", {"ticker": "X"})]
        redis_client = MagicMock()
        redis_client.xack = AsyncMock()
        config = StreamConfig(stream_name="s", group_name="g", consumer_name="c")
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)

        await recover_and_filter_pending(pending, redis_client, config, queue, "test")

        assert queue.qsize() == 1
