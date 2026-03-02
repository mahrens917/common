"""Tests for subscriber_helpers.lifecycle module."""

import asyncio

import pytest

from common.redis_protocol.streams.subscriber_helpers.lifecycle import (
    cancel_task,
    cancel_tasks,
    send_stop_sentinels,
)


class TestSendStopSentinels:
    """Tests for send_stop_sentinels."""

    def test_sends_sentinels(self):
        queue: asyncio.Queue = asyncio.Queue(maxsize=10)
        send_stop_sentinels(queue, 2, "test")
        assert queue.qsize() == 2

    def test_drains_full_queue(self):
        queue: asyncio.Queue = asyncio.Queue(maxsize=1)
        queue.put_nowait(("entry", "ticker", {}))
        send_stop_sentinels(queue, 1, "test")
        item = queue.get_nowait()
        assert item is None


class TestCancelTask:
    """Tests for cancel_task."""

    @pytest.mark.asyncio
    async def test_cancels_running_task(self):
        async def long_running():
            await asyncio.sleep(100)

        task = asyncio.create_task(long_running())
        await cancel_task(task)
        assert task.cancelled()

    @pytest.mark.asyncio
    async def test_none_task_is_noop(self):
        await cancel_task(None)


class TestCancelTasks:
    """Tests for cancel_tasks."""

    @pytest.mark.asyncio
    async def test_cancels_multiple_tasks(self):
        async def long_running():
            await asyncio.sleep(100)

        tasks = [asyncio.create_task(long_running()) for _ in range(3)]
        await cancel_tasks(tasks)
        assert all(t.cancelled() for t in tasks)
