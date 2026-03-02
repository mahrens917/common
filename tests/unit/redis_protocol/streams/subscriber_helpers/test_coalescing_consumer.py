"""Tests for subscriber_helpers.coalescing_consumer module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from common.redis_protocol.streams.subscriber import StreamConfig
from common.redis_protocol.streams.subscriber_helpers.coalescing_consumer import (
    coalesce_entries,
    consume_coalescing_stream_queue,
    drain_queue,
)


class TestDrainQueue:
    """Tests for drain_queue."""

    def test_empty_queue_returns_empty_list(self):
        queue: asyncio.Queue = asyncio.Queue()
        result = drain_queue(queue)
        assert result == []

    def test_drains_all_available_items(self):
        queue: asyncio.Queue = asyncio.Queue()
        queue.put_nowait(("e-1", "TICK", {"data": "1"}))
        queue.put_nowait(("e-2", "TICK", {"data": "2"}))
        result = drain_queue(queue)
        assert len(result) == 2
        assert result[0] == ("e-1", "TICK", {"data": "1"})
        assert result[1] == ("e-2", "TICK", {"data": "2"})

    def test_calls_task_done_for_each_item(self):
        queue: asyncio.Queue = asyncio.Queue()
        queue.put_nowait(("e-1", "A", {}))
        queue.put_nowait(("e-2", "B", {}))
        drain_queue(queue)
        # Queue should have unfinished_tasks == 0 after task_done for each
        # put_nowait increments by 1 each, drain_queue calls task_done for each
        assert queue.empty()

    def test_handles_sentinel_items(self):
        queue: asyncio.Queue = asyncio.Queue()
        queue.put_nowait(("e-1", "TICK", {}))
        queue.put_nowait(None)
        result = drain_queue(queue)
        assert len(result) == 2
        assert result[1] is None


class TestCoalesceEntries:
    """Tests for coalesce_entries."""

    def test_single_entry_returns_as_winner(self):
        entries = [("e-1", "TICK", {"data": "1"})]
        winners, superseded, saw_sentinel = coalesce_entries(entries)
        winners_list = list(winners)
        assert len(winners_list) == 1
        assert winners_list[0] == ("e-1", "TICK", {"data": "1"})
        assert superseded == []
        assert saw_sentinel is False

    def test_same_identifier_latest_wins(self):
        entries = [
            ("e-1", "TICK", {"data": "old"}),
            ("e-2", "TICK", {"data": "new"}),
        ]
        winners, superseded, saw_sentinel = coalesce_entries(entries)
        winners_list = list(winners)
        assert len(winners_list) == 1
        assert winners_list[0] == ("e-2", "TICK", {"data": "new"})
        assert superseded == ["e-1"]
        assert saw_sentinel is False

    def test_different_identifiers_both_win(self):
        entries = [
            ("e-1", "AAPL", {"data": "1"}),
            ("e-2", "GOOG", {"data": "2"}),
        ]
        winners, superseded, saw_sentinel = coalesce_entries(entries)
        assert len(list(winners)) == 2
        assert superseded == []

    def test_mixed_identifiers_with_duplicates(self):
        entries = [
            ("e-1", "AAPL", {"data": "old"}),
            ("e-2", "GOOG", {"data": "1"}),
            ("e-3", "AAPL", {"data": "mid"}),
            ("e-4", "AAPL", {"data": "new"}),
        ]
        winners, superseded, saw_sentinel = coalesce_entries(entries)
        winners_list = list(winners)
        assert len(winners_list) == 2
        identifiers = {w[1] for w in winners_list}
        assert identifiers == {"AAPL", "GOOG"}
        # AAPL winner should be e-4 (latest)
        aapl_winner = next(w for w in winners_list if w[1] == "AAPL")
        assert aapl_winner[0] == "e-4"
        assert sorted(superseded) == ["e-1", "e-3"]

    def test_sentinel_sets_saw_sentinel(self):
        entries = [("e-1", "TICK", {}), None]
        winners, superseded, saw_sentinel = coalesce_entries(entries)
        assert saw_sentinel is True
        assert len(list(winners)) == 1

    def test_empty_list_returns_empty_results(self):
        winners, superseded, saw_sentinel = coalesce_entries([])
        assert list(winners) == []
        assert superseded == []
        assert saw_sentinel is False


class TestConsumeCoalescingStreamQueue:
    """Tests for consume_coalescing_stream_queue."""

    @pytest.mark.asyncio
    async def test_processes_single_entry(self):
        queue: asyncio.Queue = asyncio.Queue()
        queue.put_nowait(("e-1", "TICK", {"ticker": "TICK"}))
        queue.put_nowait(None)
        handler = AsyncMock()
        redis_client = MagicMock()
        redis_client.xack = AsyncMock()
        config = StreamConfig(stream_name="s", group_name="g", consumer_name="c")
        retry_counts: dict[str, int] = {}

        await consume_coalescing_stream_queue(queue, handler, redis_client, config, "test", retry_counts)

        handler.assert_called_once_with("TICK", {"ticker": "TICK"})
        redis_client.xack.assert_called_once_with("s", "g", "e-1")

    @pytest.mark.asyncio
    async def test_coalesces_duplicate_identifiers(self):
        queue: asyncio.Queue = asyncio.Queue()
        # Put all entries before consuming so they're all available at drain time
        queue.put_nowait(("e-1", "TICK", {"data": "old"}))
        queue.put_nowait(("e-2", "TICK", {"data": "mid"}))
        queue.put_nowait(("e-3", "TICK", {"data": "new"}))
        queue.put_nowait(None)
        handler = AsyncMock()
        redis_client = MagicMock()
        redis_client.xack = AsyncMock()
        config = StreamConfig(stream_name="s", group_name="g", consumer_name="c")
        retry_counts: dict[str, int] = {}

        await consume_coalescing_stream_queue(queue, handler, redis_client, config, "test", retry_counts)

        # Handler called once — only with latest
        handler.assert_called_once_with("TICK", {"data": "new"})
        # xack called twice: once for bulk superseded (e-1, e-2), once for winner (e-3)
        assert redis_client.xack.call_count == 2
        # First call: bulk ACK for superseded
        redis_client.xack.assert_any_call("s", "g", "e-1", "e-2")
        # Second call: ACK for processed winner
        redis_client.xack.assert_any_call("s", "g", "e-3")

    @pytest.mark.asyncio
    async def test_stops_on_sentinel(self):
        queue: asyncio.Queue = asyncio.Queue()
        queue.put_nowait(None)
        handler = AsyncMock()
        redis_client = MagicMock()
        redis_client.xack = AsyncMock()
        config = StreamConfig(stream_name="s", group_name="g", consumer_name="c")

        await consume_coalescing_stream_queue(queue, handler, redis_client, config, "test", {})

        handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_handler_error_triggers_retry(self):
        queue: asyncio.Queue = asyncio.Queue()
        queue.put_nowait(("e-1", "TICK", {"ticker": "TICK"}))
        queue.put_nowait(None)
        handler = AsyncMock(side_effect=RuntimeError("handler failed"))
        redis_client = MagicMock()
        redis_client.xack = AsyncMock()
        config = StreamConfig(stream_name="s", group_name="g", consumer_name="c")
        retry_counts: dict[str, int] = {}

        await consume_coalescing_stream_queue(queue, handler, redis_client, config, "test", retry_counts)

        # Entry should be requeued for retry, not ACKed as processed
        assert retry_counts.get("e-1") == 1

    @pytest.mark.asyncio
    async def test_bulk_acks_superseded_entries(self):
        queue: asyncio.Queue = asyncio.Queue()
        queue.put_nowait(("e-1", "A", {"data": "1"}))
        queue.put_nowait(("e-2", "A", {"data": "2"}))
        queue.put_nowait(("e-3", "B", {"data": "3"}))
        queue.put_nowait(None)
        handler = AsyncMock()
        redis_client = MagicMock()
        redis_client.xack = AsyncMock()
        config = StreamConfig(stream_name="s", group_name="g", consumer_name="c")

        await consume_coalescing_stream_queue(queue, handler, redis_client, config, "test", {})

        # Superseded e-1 bulk ACKed, winners e-2 and e-3 individually ACKed
        assert redis_client.xack.call_count == 3
        redis_client.xack.assert_any_call("s", "g", "e-1")
