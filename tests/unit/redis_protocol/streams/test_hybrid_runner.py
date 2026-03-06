"""Tests for hybrid stream + timer runner."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.redis_protocol.streams.hybrid_runner import HybridConfig, _timer_loop, run_hybrid_mode
from common.redis_protocol.streams.subscriber import StreamConfig

_TEST_STREAM = "stream:test"
_TEST_GROUP = "test-group"
_TEST_CONSUMER = "test-consumer-0"
_MIN_EXPECTED_CALLS = 2


def _make_hybrid_config(timer_interval: int = 1) -> HybridConfig:
    return HybridConfig(
        stream_config=StreamConfig(
            stream_name=_TEST_STREAM,
            group_name=_TEST_GROUP,
            consumer_name=_TEST_CONSUMER,
        ),
        timer_interval_seconds=timer_interval,
    )


class TestHybridConfig:
    """Tests for HybridConfig dataclass."""

    def test_creation(self):
        config = _make_hybrid_config(timer_interval=30)

        assert config.timer_interval_seconds == 30
        assert config.stream_config.stream_name == _TEST_STREAM
        assert config.stream_config.group_name == _TEST_GROUP


class TestTimerLoop:
    """Tests for the internal timer loop."""

    @pytest.mark.asyncio
    async def test_timer_calls_on_timer(self):
        call_count = 0

        async def on_timer():
            nonlocal call_count
            call_count += 1

        task = asyncio.create_task(_timer_loop(0, on_timer, "test"))
        await asyncio.sleep(0.05)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        assert call_count >= 1

    @pytest.mark.asyncio
    async def test_timer_continues_after_callback_error(self):
        call_count = 0

        async def on_timer():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("boom")

        task = asyncio.create_task(_timer_loop(0, on_timer, "test"))
        await asyncio.sleep(0.05)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        assert call_count >= _MIN_EXPECTED_CALLS


class TestRunHybridMode:
    """Tests for the run_hybrid_mode orchestrator."""

    @pytest.mark.asyncio
    async def test_starts_subscriber_and_timer(self):
        config = _make_hybrid_config(timer_interval=1)
        on_update = AsyncMock()
        on_timer = AsyncMock()
        redis_client = MagicMock()

        mock_subscriber = MagicMock()
        mock_subscriber.start = AsyncMock()
        mock_subscriber.stop = AsyncMock()
        mock_subscriber.reader_task = None
        mock_subscriber.consumer_tasks = []

        with patch(
            "common.redis_protocol.streams.hybrid_runner.RedisStreamSubscriber",
            return_value=mock_subscriber,
        ):
            task = asyncio.create_task(run_hybrid_mode(redis_client, config, on_update, on_timer, subscriber_name="test"))
            await asyncio.sleep(0.05)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

        mock_subscriber.start.assert_awaited_once()
        mock_subscriber.stop.assert_awaited_once()
