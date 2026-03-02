"""Tests for RedisStreamSubscriber."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from common.redis_protocol.streams.subscriber import (
    RedisStreamSubscriber,
    StreamConfig,
)


class TestStreamConfig:
    """Tests for StreamConfig dataclass."""

    def test_default_values(self):
        config = StreamConfig(
            stream_name="stream:test",
            group_name="group",
            consumer_name="consumer",
        )
        assert config.identifier_field == "ticker"
        assert config.block_ms == 5000
        assert config.batch_size == 100
        assert config.queue_size == 10000
        assert config.num_consumers == 1

    def test_default_coalesce_is_false(self):
        config = StreamConfig(
            stream_name="stream:test",
            group_name="group",
            consumer_name="consumer",
        )
        assert config.coalesce is False


class TestRedisStreamSubscriber:
    """Tests for RedisStreamSubscriber lifecycle."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.xgroup_create = AsyncMock(return_value=True)
        redis.xautoclaim = AsyncMock(return_value=(b"0-0", [], []))
        redis.xreadgroup = AsyncMock(return_value=None)
        redis.xack = AsyncMock(return_value=1)
        return redis

    @pytest.fixture
    def config(self):
        return StreamConfig(
            stream_name="stream:test",
            group_name="test-group",
            consumer_name="test-consumer",
        )

    @pytest.fixture
    def handler(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_start_creates_consumer_group(self, mock_redis, config, handler):
        subscriber = RedisStreamSubscriber(mock_redis, handler, config=config, subscriber_name="test")
        await subscriber.start()
        await subscriber.stop()

        mock_redis.xgroup_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_recovers_pending(self, mock_redis, config, handler):
        import time

        recent_ts = str(int(time.time() * 1000))
        recent_entry_id = f"{recent_ts}-0".encode()
        mock_redis.xautoclaim = AsyncMock(
            return_value=(
                b"0-0",
                [(recent_entry_id, {b"ticker": b"AAPL", b"payload": b'{"ticker": "AAPL"}'})],
                [],
            )
        )
        subscriber = RedisStreamSubscriber(mock_redis, handler, config=config, subscriber_name="test")
        await subscriber.start()
        await asyncio.sleep(0.05)
        await subscriber.stop()

        handler.assert_called()

    @pytest.mark.asyncio
    async def test_stop_is_idempotent(self, mock_redis, config, handler):
        subscriber = RedisStreamSubscriber(mock_redis, handler, config=config, subscriber_name="test")
        await subscriber.start()
        await subscriber.stop()
        await subscriber.stop()

    @pytest.mark.asyncio
    async def test_start_is_idempotent(self, mock_redis, config, handler):
        subscriber = RedisStreamSubscriber(mock_redis, handler, config=config, subscriber_name="test")
        await subscriber.start()
        await subscriber.start()
        await subscriber.stop()

        mock_redis.xgroup_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_running_property(self, mock_redis, config, handler):
        subscriber = RedisStreamSubscriber(mock_redis, handler, config=config, subscriber_name="test")
        assert not subscriber.running
        await subscriber.start()
        assert subscriber.running
        await subscriber.stop()
        assert not subscriber.running

    @pytest.mark.asyncio
    async def test_reader_task_property(self, mock_redis, config, handler):
        subscriber = RedisStreamSubscriber(mock_redis, handler, config=config, subscriber_name="test")
        assert subscriber.reader_task is None
        await subscriber.start()
        assert subscriber.reader_task is not None
        await subscriber.stop()
        assert subscriber.reader_task is None

    @pytest.mark.asyncio
    async def test_consumer_tasks_property(self, mock_redis, config, handler):
        subscriber = RedisStreamSubscriber(mock_redis, handler, config=config, subscriber_name="test")
        assert subscriber.consumer_tasks == []
        await subscriber.start()
        assert len(subscriber.consumer_tasks) == 1
        await subscriber.stop()
        assert subscriber.consumer_tasks == []
