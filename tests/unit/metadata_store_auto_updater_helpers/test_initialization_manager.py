import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.exceptions import DataError
from common.metadata_store_auto_updater_helpers.initialization_manager import (
    InitializationManager,
)


class TestInitializationManager:
    @pytest.fixture
    def manager(self):
        return InitializationManager()

    @pytest.fixture
    def mock_redis(self):
        client = AsyncMock()
        client.config_set = AsyncMock()
        client.aclose = AsyncMock()
        return client

    @pytest.fixture
    def mock_metadata_store(self):
        store = AsyncMock()
        store.initialize = AsyncMock()
        return store

    @pytest.mark.asyncio
    async def test_initialize_success(self, manager, mock_redis, mock_metadata_store):
        with (
            patch(
                "common.metadata_store_auto_updater_helpers.initialization_manager.perform_redis_health_check",
                return_value=True,
            ),
            patch(
                "common.metadata_store_auto_updater_helpers.initialization_manager.get_redis_connection",
                return_value=mock_redis,
            ) as mock_get_redis,
        ):

            await manager.initialize(mock_metadata_store)

            assert manager.redis_client == mock_redis
            assert manager.pubsub_client == mock_redis
            assert mock_get_redis.call_count == 2  # Once for redis, once for pubsub
            mock_metadata_store.initialize.assert_awaited_once()
            mock_redis.config_set.assert_awaited_once_with("notify-keyspace-events", "KEA")

    @pytest.mark.asyncio
    async def test_initialize_redis_client_failure(self, manager, mock_metadata_store):
        with (
            patch(
                "common.metadata_store_auto_updater_helpers.initialization_manager.perform_redis_health_check",
                return_value=True,
            ),
            patch(
                "common.metadata_store_auto_updater_helpers.initialization_manager.get_redis_connection",
                return_value=None,
            ),
        ):

            with pytest.raises(DataError, match="Failed to initialize redis client"):
                await manager.initialize(mock_metadata_store)

    @pytest.mark.asyncio
    async def test_initialize_pubsub_client_failure(self, manager, mock_redis, mock_metadata_store):
        with (
            patch(
                "common.metadata_store_auto_updater_helpers.initialization_manager.perform_redis_health_check",
                return_value=True,
            ),
            patch(
                "common.metadata_store_auto_updater_helpers.initialization_manager.get_redis_connection",
                side_effect=[mock_redis, None],
            ),
        ):

            with pytest.raises(DataError, match="Failed to initialize pubsub client"):
                await manager.initialize(mock_metadata_store)

    @pytest.mark.asyncio
    async def test_ensure_redis_pool_ready_retry_success(self, manager):
        with (
            patch(
                "common.metadata_store_auto_updater_helpers.initialization_manager.perform_redis_health_check",
                side_effect=[False, False, True],
            ) as mock_check,
            patch("asyncio.sleep", return_value=None),
        ):  # speed up test

            await manager._ensure_redis_pool_ready(max_retries=5)
            assert mock_check.call_count == 3

    @pytest.mark.asyncio
    async def test_ensure_redis_pool_ready_failure(self, manager):
        with (
            patch(
                "common.metadata_store_auto_updater_helpers.initialization_manager.perform_redis_health_check",
                return_value=False,
            ) as mock_check,
            patch("asyncio.sleep", return_value=None),
        ):

            with pytest.raises(ConnectionError, match="Redis pool not ready"):
                await manager._ensure_redis_pool_ready(max_retries=3)
            assert mock_check.call_count == 3

    @pytest.mark.asyncio
    async def test_ensure_redis_pool_ready_exception(self, manager):
        with (
            patch(
                "common.metadata_store_auto_updater_helpers.initialization_manager.perform_redis_health_check",
                side_effect=RuntimeError("Connection failed"),
            ) as mock_check,
            patch("asyncio.sleep", return_value=None),
        ):

            with pytest.raises(ConnectionError, match="Redis pool not ready"):
                await manager._ensure_redis_pool_ready(max_retries=2)
            assert mock_check.call_count == 2

    @pytest.mark.asyncio
    async def test_cleanup(self, manager, mock_redis):
        manager.redis_client = mock_redis
        manager.pubsub_client = mock_redis

        await manager.cleanup()

        assert mock_redis.aclose.call_count == 2
        assert manager.redis_client is None
        assert manager.pubsub_client is None

    @pytest.mark.asyncio
    async def test_cleanup_error(self, manager, mock_redis):
        manager.redis_client = mock_redis
        mock_redis.aclose.side_effect = Exception("Close error")

        await manager.cleanup()

        # Should not raise
        assert manager.redis_client is None
