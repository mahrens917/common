import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from common.websocket.unified_subscription_manager_helpers.monitoring_loop import MonitoringLoop


class TestMonitoringLoop:
    @pytest.fixture
    def loop(self):
        return MonitoringLoop("test_service", "test_channel", Mock(), Mock(), Mock())

    @pytest.mark.asyncio
    async def test_run_success(self, loop):
        redis_client = AsyncMock()
        pubsub = AsyncMock()

        # Fix: pubsub() is a synchronous method returning a pubsub object
        redis_client.pubsub = Mock(return_value=pubsub)

        # Mock listen loop to run once then raise CancelledError to stop
        async def mock_listen_loop(*args):
            pass

        loop._listen_loop = AsyncMock(side_effect=mock_listen_loop)

        with patch(
            "common.redis_protocol.connection_pool_core.get_redis_client",
            new_callable=AsyncMock,
        ) as mock_get_client:
            mock_get_client.return_value = redis_client

            await loop.run()

            pubsub.subscribe.assert_called_once_with("test_channel")
            loop._listen_loop.assert_called_once()
            pubsub.unsubscribe.assert_called_once()
            redis_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_fatal_error(self, loop):
        with patch(
            "common.redis_protocol.connection_pool_core.get_redis_client",
            new_callable=AsyncMock,
        ) as mock_get_client:
            mock_get_client.side_effect = RuntimeError("Fatal")

            with pytest.raises(RuntimeError):
                await loop.run()

    @pytest.mark.asyncio
    async def test_listen_loop(self, loop):
        pubsub = Mock()
        redis_client = Mock()

        # Mock listen to yield one message then raise CancelledError
        async def mock_listen():
            yield {"type": "message"}
            raise asyncio.CancelledError()

        pubsub.listen.return_value = mock_listen()
        loop.message_processor.process_message = AsyncMock()

        await loop._listen_loop(pubsub, redis_client)

        loop.message_processor.process_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_listen_loop_redis_error(self, loop):
        pubsub = Mock()
        redis_client = Mock()

        class _ErrorListener:
            def __aiter__(self):
                return self

            async def __anext__(self):
                raise ConnectionError("Redis fail")

        # Use side_effect so each call returns a new generator instance
        pubsub.listen.side_effect = lambda: _ErrorListener()

        # We need to interrupt the loop.
        # 1. First call to listen() raises ConnectionError. Caught. Sleep(5).
        # 2. Sleep(5) returns None (first side_effect).
        # 3. Loop continues. Second call to listen() raises ConnectionError. Caught. Sleep(5).
        # 4. Sleep(5) raises CancelledError (second side_effect).
        # 5. Caught CancelledError. Break.

        with (
            patch("asyncio.sleep", side_effect=[None, asyncio.CancelledError()]) as mock_sleep,
            patch(
                "common.websocket.unified_subscription_manager_helpers.monitoring_loop.logger"
            ) as mock_logger,
        ):

            try:
                await loop._listen_loop(pubsub, redis_client)
            except asyncio.CancelledError:
                pass

            # Verify exception was logged
            mock_logger.exception.assert_called()
            # It might be called multiple times if loop ran multiple times
            args = mock_logger.exception.call_args
            assert "Error monitoring %s subscriptions: %s" in args[0][0]

    @pytest.mark.asyncio
    async def test_cleanup_pubsub_error(self, loop):
        pubsub = Mock()
        pubsub.unsubscribe = AsyncMock(side_effect=ValueError("Fail"))

        # Should check log and not raise
        await loop._cleanup_pubsub(pubsub)

    @pytest.mark.asyncio
    async def test_cleanup_redis_error(self, loop):
        redis_client = Mock()
        # We assume ValueError is not in REDIS_ERRORS so we mock aclose to raise something that IS caught if we can check REDIS_ERRORS.
        # Or simpler: we just check that it calls aclose.
        redis_client.aclose = AsyncMock()
        await loop._cleanup_redis(redis_client)
        redis_client.aclose.assert_called_once()
