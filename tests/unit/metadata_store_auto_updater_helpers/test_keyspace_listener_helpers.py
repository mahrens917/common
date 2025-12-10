import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from common.metadata_store_auto_updater_helpers.keyspace_listener import KeyspaceListener
from common.metadata_store_auto_updater_helpers.keyspace_listener_helpers.event_handler import (
    EventHandler,
)
from common.metadata_store_auto_updater_helpers.keyspace_listener_helpers.pubsub_manager import (
    PubsubManager,
)
from common.metadata_store_auto_updater_helpers.keyspace_listener_helpers.service_extractor import (
    ServiceExtractor,
)


class TestServiceExtractor:
    def test_extract_known_service(self):
        extractor = ServiceExtractor()
        assert extractor.extract_service_name("history:deribit:BTC-PERPETUAL") == "deribit"
        assert extractor.extract_service_name("history:kalshi:ticker") == "kalshi"

    def test_extract_weather_station(self):
        extractor = ServiceExtractor()
        assert extractor.extract_service_name("history:KAUS:123456") == "weather"
        assert extractor.extract_service_name("history:KJFK:123456") == "weather"

    def test_extract_unknown_service(self):
        extractor = ServiceExtractor()
        assert extractor.extract_service_name("history:unknown:key") is None

    def test_extract_invalid_key_format(self):
        extractor = ServiceExtractor()
        assert extractor.extract_service_name("invalid:key") is None


class TestEventHandler:
    @pytest.fixture
    def pending_updates(self):
        from collections import defaultdict

        return defaultdict(int)

    @pytest.fixture
    def batch_lock(self):
        return asyncio.Lock()

    @pytest.fixture
    def service_extractor(self):
        extractor = Mock(spec=ServiceExtractor)
        extractor.extract_service_name.return_value = "test_service"
        return extractor

    @pytest.fixture
    def handler(self, pending_updates, batch_lock, service_extractor):
        return EventHandler(pending_updates, batch_lock, service_extractor)

    @pytest.mark.asyncio
    async def test_handle_valid_event(self, handler, pending_updates):
        message = {
            "channel": b"__keyspace@0__:history:test_service:key",
            "data": b"hset",
        }
        await handler.handle_keyspace_event(message)
        assert pending_updates["test_service"] == 1

    @pytest.mark.asyncio
    async def test_handle_event_decoded_strings(self, handler, pending_updates):
        message = {
            "channel": "__keyspace@0__:history:test_service:key",
            "data": "set",
        }
        await handler.handle_keyspace_event(message)
        assert pending_updates["test_service"] == 1

    @pytest.mark.asyncio
    async def test_ignore_irrelevant_operation(self, handler, pending_updates):
        message = {
            "channel": b"__keyspace@0__:history:test_service:key",
            "data": b"del",
        }
        await handler.handle_keyspace_event(message)
        assert len(pending_updates) == 0

    @pytest.mark.asyncio
    async def test_ignore_invalid_channel_format(self, handler, pending_updates):
        message = {
            "channel": b"invalid_channel",
            "data": b"hset",
        }
        await handler.handle_keyspace_event(message)
        assert len(pending_updates) == 0

    @pytest.mark.asyncio
    async def test_handle_extractor_returns_none(self, handler, pending_updates, service_extractor):
        service_extractor.extract_service_name.return_value = None
        message = {
            "channel": b"__keyspace@0__:history:unknown:key",
            "data": b"hset",
        }
        await handler.handle_keyspace_event(message)
        assert len(pending_updates) == 0

    @pytest.mark.asyncio
    async def test_handle_exception(self, handler):
        # Malformed message causing exception
        await handler.handle_keyspace_event(None)
        # Should not raise, just log error


class TestPubsubManager:
    @pytest.fixture
    def mock_redis(self):
        client = AsyncMock()
        pubsub = AsyncMock()
        client.pubsub = Mock(return_value=pubsub)
        return client

    @pytest.fixture
    def mock_event_handler(self):
        return AsyncMock()

    @pytest.fixture
    def manager(self, mock_redis, mock_event_handler):
        return PubsubManager(mock_redis, mock_event_handler)

    @pytest.mark.asyncio
    async def test_listen_with_retry_success(self, manager, mock_redis):
        mock_pubsub = mock_redis.pubsub.return_value

        # Mock listen to yield one message then stop (simulating end or shutdown check)
        # We can mock listen() to be an async generator
        async def mock_listen():
            yield {"type": "pmessage", "data": "test"}
            manager.request_shutdown()  # Trigger shutdown to exit loop

        mock_pubsub.listen = mock_listen

        with patch(
            "common.metadata_store_auto_updater_helpers.keyspace_listener_helpers.pubsub_manager.perform_redis_health_check",
            return_value=True,
        ):
            await manager.listen_with_retry()

        mock_pubsub.psubscribe.assert_awaited_once()
        manager.event_handler.handle_keyspace_event.assert_awaited()
        mock_pubsub.close.assert_awaited()

    @pytest.mark.asyncio
    async def test_listen_with_retry_health_check_failure(self, manager):
        with (
            patch(
                "common.metadata_store_auto_updater_helpers.keyspace_listener_helpers.pubsub_manager.perform_redis_health_check",
                return_value=False,
            ),
            patch("asyncio.sleep", return_value=None),
        ):

            await manager.listen_with_retry()

            # Should try 5 times (max_retries)
            # Since health check returns False, it raises ConnectionError caught in loop
            # The loop runs until max_retries is hit or successful break
            # Here it hits max retries

    @pytest.mark.asyncio
    async def test_listen_with_retry_redis_error(self, manager, mock_redis):
        # Mock pubsub to raise error
        mock_redis.pubsub.side_effect = ConnectionError("Redis down")

        with (
            patch(
                "common.metadata_store_auto_updater_helpers.keyspace_listener_helpers.pubsub_manager.perform_redis_health_check",
                return_value=True,
            ),
            patch("asyncio.sleep", return_value=None),
        ):

            await manager.listen_with_retry()

            assert mock_redis.pubsub.call_count == 5

    @pytest.mark.asyncio
    async def test_listen_shutdown_requested(self, manager):
        manager.request_shutdown()
        await manager.listen_with_retry()
        # Should exit immediately
        # Actually, verify_redis_health is called first? No, check is `while not self._shutdown_requested`
        # So it shouldn't even call verify_redis_health
        # Wait, verify_redis_health IS called inside loop. But loop condition is checked first.
        # So nothing called.

    @pytest.mark.asyncio
    async def test_cancelled_error(self, manager):
        with patch(
            "common.metadata_store_auto_updater_helpers.keyspace_listener_helpers.pubsub_manager.perform_redis_health_check",
            side_effect=asyncio.CancelledError,
        ):
            with pytest.raises(asyncio.CancelledError):
                await manager.listen_with_retry()


class TestKeyspaceListener:
    @pytest.fixture
    def mock_client(self):
        return AsyncMock()

    @pytest.fixture
    def listener(self, mock_client):
        return KeyspaceListener(mock_client, {}, asyncio.Lock())

    @pytest.mark.asyncio
    async def test_listen_delegates(self, listener):
        with patch.object(
            listener._pubsub_manager, "listen_with_retry", new_callable=AsyncMock
        ) as mock_listen:
            await listener.listen()
            mock_listen.assert_awaited_once()

    def test_shutdown_delegates(self, listener):
        with patch.object(listener._pubsub_manager, "request_shutdown") as mock_shutdown:
            listener.request_shutdown()
            mock_shutdown.assert_called_once()
