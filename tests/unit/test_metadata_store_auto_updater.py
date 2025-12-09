"""Tests for metadata_store_auto_updater module."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.common.metadata_store_auto_updater import MetadataStoreAutoUpdater


class TestMetadataStoreAutoUpdater:
    """Tests for MetadataStoreAutoUpdater class."""

    def test_init_with_metadata_store(self) -> None:
        """Initializes with provided metadata store."""
        mock_store = MagicMock()

        updater = MetadataStoreAutoUpdater(metadata_store=mock_store)

        assert updater.metadata_store is mock_store

    def test_init_creates_metadata_store_when_not_provided(self) -> None:
        """Creates MetadataStore when not provided."""
        with patch("src.common.metadata_store_auto_updater.MetadataStore") as mock_store_class:
            mock_store = MagicMock()
            mock_store_class.return_value = mock_store

            updater = MetadataStoreAutoUpdater()

        assert updater.metadata_store is mock_store
        mock_store_class.assert_called_once()

    def test_init_sets_default_batch_interval(self) -> None:
        """Sets default batch_interval_seconds to 1.0."""
        updater = MetadataStoreAutoUpdater(metadata_store=MagicMock())

        assert updater.batch_interval_seconds == 1.0

    def test_init_creates_empty_pending_updates(self) -> None:
        """Creates empty pending_updates defaultdict."""
        updater = MetadataStoreAutoUpdater(metadata_store=MagicMock())

        assert isinstance(updater.pending_updates, defaultdict)
        assert len(updater.pending_updates) == 0

    def test_init_sets_tasks_to_none(self) -> None:
        """Sets all task attributes to None."""
        updater = MetadataStoreAutoUpdater(metadata_store=MagicMock())

        assert updater._listener_task is None
        assert updater._batch_processor_task is None
        assert updater._time_window_updater_task is None

    def test_init_sets_shutdown_requested_to_false(self) -> None:
        """Sets _shutdown_requested to False."""
        updater = MetadataStoreAutoUpdater(metadata_store=MagicMock())

        assert updater._shutdown_requested is False

    def test_init_creates_init_manager(self) -> None:
        """Creates InitializationManager."""
        updater = MetadataStoreAutoUpdater(metadata_store=MagicMock())

        assert updater.init_manager is not None

    def test_init_sets_helpers_to_none(self) -> None:
        """Sets helper components to None until initialized."""
        updater = MetadataStoreAutoUpdater(metadata_store=MagicMock())

        assert updater.keyspace_listener is None
        assert updater.batch_processor is None
        assert updater.time_window_updater is None
        assert updater.metadata_initializer is None


class TestMetadataStoreAutoUpdaterInitialize:
    """Tests for MetadataStoreAutoUpdater.initialize method."""

    @pytest.mark.asyncio
    async def test_initialize_calls_init_manager(self) -> None:
        """Calls init_manager.initialize with metadata_store."""
        mock_store = MagicMock()
        updater = MetadataStoreAutoUpdater(metadata_store=mock_store)
        updater.init_manager = MagicMock()
        updater.init_manager.initialize = AsyncMock()
        updater.init_manager.pubsub_client = MagicMock()
        updater.init_manager.redis_client = MagicMock()

        await updater.initialize()

        updater.init_manager.initialize.assert_called_once_with(mock_store)

    @pytest.mark.asyncio
    async def test_initialize_creates_keyspace_listener(self) -> None:
        """Creates KeyspaceListener with correct args."""
        mock_store = MagicMock()
        updater = MetadataStoreAutoUpdater(metadata_store=mock_store)
        updater.init_manager = MagicMock()
        updater.init_manager.initialize = AsyncMock()
        mock_pubsub = MagicMock()
        updater.init_manager.pubsub_client = mock_pubsub
        updater.init_manager.redis_client = MagicMock()

        with patch(
            "src.common.metadata_store_auto_updater.KeyspaceListener"
        ) as mock_listener_class:
            await updater.initialize()

        mock_listener_class.assert_called_once_with(
            mock_pubsub, updater.pending_updates, updater._batch_lock
        )

    @pytest.mark.asyncio
    async def test_initialize_creates_batch_processor(self) -> None:
        """Creates BatchProcessor with correct args."""
        mock_store = MagicMock()
        updater = MetadataStoreAutoUpdater(metadata_store=mock_store)
        updater.init_manager = MagicMock()
        updater.init_manager.initialize = AsyncMock()
        updater.init_manager.pubsub_client = MagicMock()
        updater.init_manager.redis_client = MagicMock()

        with patch("src.common.metadata_store_auto_updater.BatchProcessor") as mock_processor_class:
            await updater.initialize()

        mock_processor_class.assert_called_once_with(
            mock_store, updater.pending_updates, updater._batch_lock, 1.0
        )

    @pytest.mark.asyncio
    async def test_initialize_creates_time_window_updater(self) -> None:
        """Creates TimeWindowUpdater with correct args."""
        mock_store = MagicMock()
        updater = MetadataStoreAutoUpdater(metadata_store=mock_store)
        updater.init_manager = MagicMock()
        updater.init_manager.initialize = AsyncMock()
        updater.init_manager.pubsub_client = MagicMock()
        mock_redis = MagicMock()
        updater.init_manager.redis_client = mock_redis

        with patch(
            "src.common.metadata_store_auto_updater.TimeWindowUpdater"
        ) as mock_updater_class:
            await updater.initialize()

        mock_updater_class.assert_called_once_with(mock_store, mock_redis)

    @pytest.mark.asyncio
    async def test_initialize_creates_metadata_initializer(self) -> None:
        """Creates MetadataInitializer with correct args."""
        mock_store = MagicMock()
        updater = MetadataStoreAutoUpdater(metadata_store=mock_store)
        updater.init_manager = MagicMock()
        updater.init_manager.initialize = AsyncMock()
        updater.init_manager.pubsub_client = MagicMock()
        mock_redis = MagicMock()
        updater.init_manager.redis_client = mock_redis

        with patch("src.common.metadata_store_auto_updater.MetadataInitializer") as mock_init_class:
            await updater.initialize()

        mock_init_class.assert_called_once_with(mock_store, mock_redis)


class TestMetadataStoreAutoUpdaterStart:
    """Tests for MetadataStoreAutoUpdater.start method."""

    @pytest.mark.asyncio
    async def test_start_logs_warning_if_already_started(self) -> None:
        """Logs warning if already started."""
        mock_store = MagicMock()
        updater = MetadataStoreAutoUpdater(metadata_store=mock_store)
        updater._listener_task = MagicMock()

        with patch("src.common.metadata_store_auto_updater.logger") as mock_logger:
            await updater.start()

        mock_logger.warning.assert_called_once()
        assert "already started" in mock_logger.warning.call_args[0][0]

    @pytest.mark.asyncio
    async def test_start_calls_initialize(self) -> None:
        """Calls initialize method."""
        mock_store = MagicMock()
        updater = MetadataStoreAutoUpdater(metadata_store=mock_store)
        updater.initialize = AsyncMock()
        mock_initializer = MagicMock()
        mock_initializer.initialize_from_existing_keys = AsyncMock()
        updater.metadata_initializer = mock_initializer
        mock_listener = MagicMock()
        mock_listener.listen = AsyncMock()
        updater.keyspace_listener = mock_listener
        mock_processor = MagicMock()
        mock_processor.run = AsyncMock()
        updater.batch_processor = mock_processor
        mock_time_updater = MagicMock()
        mock_time_updater.run = AsyncMock()
        updater.time_window_updater = mock_time_updater

        await updater.start()

        updater.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_calls_initialize_from_existing_keys(self) -> None:
        """Calls metadata_initializer.initialize_from_existing_keys."""
        mock_store = MagicMock()
        updater = MetadataStoreAutoUpdater(metadata_store=mock_store)
        updater.initialize = AsyncMock()
        mock_initializer = MagicMock()
        mock_initializer.initialize_from_existing_keys = AsyncMock()
        updater.metadata_initializer = mock_initializer
        mock_listener = MagicMock()
        mock_listener.listen = AsyncMock()
        updater.keyspace_listener = mock_listener
        mock_processor = MagicMock()
        mock_processor.run = AsyncMock()
        updater.batch_processor = mock_processor
        mock_time_updater = MagicMock()
        mock_time_updater.run = AsyncMock()
        updater.time_window_updater = mock_time_updater

        await updater.start()

        mock_initializer.initialize_from_existing_keys.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_creates_background_tasks(self) -> None:
        """Creates background tasks for listener, processor, and time updater."""
        mock_store = MagicMock()
        updater = MetadataStoreAutoUpdater(metadata_store=mock_store)
        updater.initialize = AsyncMock()
        mock_initializer = MagicMock()
        mock_initializer.initialize_from_existing_keys = AsyncMock()
        updater.metadata_initializer = mock_initializer

        mock_listener = MagicMock()
        mock_listener.listen = AsyncMock()
        updater.keyspace_listener = mock_listener

        mock_processor = MagicMock()
        mock_processor.run = AsyncMock()
        updater.batch_processor = mock_processor

        mock_time_updater = MagicMock()
        mock_time_updater.run = AsyncMock()
        updater.time_window_updater = mock_time_updater

        await updater.start()

        assert updater._listener_task is not None
        assert updater._batch_processor_task is not None
        assert updater._time_window_updater_task is not None


class TestMetadataStoreAutoUpdaterStop:
    """Tests for MetadataStoreAutoUpdater.stop method."""

    @pytest.mark.asyncio
    async def test_stop_sets_shutdown_requested(self) -> None:
        """Sets _shutdown_requested to True."""
        mock_store = MagicMock()
        mock_store.cleanup = AsyncMock()
        updater = MetadataStoreAutoUpdater(metadata_store=mock_store)
        updater.init_manager = MagicMock()
        updater.init_manager.cleanup = AsyncMock()

        await updater.stop()

        assert updater._shutdown_requested is True

    @pytest.mark.asyncio
    async def test_stop_requests_shutdown_on_components(self) -> None:
        """Requests shutdown on all helper components."""
        mock_store = MagicMock()
        mock_store.cleanup = AsyncMock()
        updater = MetadataStoreAutoUpdater(metadata_store=mock_store)
        updater.init_manager = MagicMock()
        updater.init_manager.cleanup = AsyncMock()

        mock_listener = MagicMock()
        updater.keyspace_listener = mock_listener
        mock_processor = MagicMock()
        updater.batch_processor = mock_processor
        mock_time_updater = MagicMock()
        updater.time_window_updater = mock_time_updater

        await updater.stop()

        mock_listener.request_shutdown.assert_called_once()
        mock_processor.request_shutdown.assert_called_once()
        mock_time_updater.request_shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_cancels_running_tasks(self) -> None:
        """Cancels running tasks."""
        mock_store = MagicMock()
        mock_store.cleanup = AsyncMock()
        updater = MetadataStoreAutoUpdater(metadata_store=mock_store)
        updater.init_manager = MagicMock()
        updater.init_manager.cleanup = AsyncMock()

        mock_task = MagicMock()
        mock_task.done.return_value = False
        mock_task.cancel = MagicMock()

        async def wait_side_effect(task, timeout):
            raise asyncio.CancelledError()

        updater._listener_task = mock_task

        with patch("asyncio.wait_for", side_effect=wait_side_effect):
            await updater.stop()

        mock_task.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_calls_cleanup_on_init_manager(self) -> None:
        """Calls cleanup on init_manager."""
        mock_store = MagicMock()
        mock_store.cleanup = AsyncMock()
        updater = MetadataStoreAutoUpdater(metadata_store=mock_store)
        updater.init_manager = MagicMock()
        updater.init_manager.cleanup = AsyncMock()

        await updater.stop()

        updater.init_manager.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_calls_cleanup_on_metadata_store(self) -> None:
        """Calls cleanup on metadata_store."""
        mock_store = MagicMock()
        mock_store.cleanup = AsyncMock()
        updater = MetadataStoreAutoUpdater(metadata_store=mock_store)
        updater.init_manager = MagicMock()
        updater.init_manager.cleanup = AsyncMock()

        await updater.stop()

        mock_store.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_handles_metadata_store_cleanup_error(self) -> None:
        """Handles error during metadata store cleanup."""
        mock_store = MagicMock()
        mock_store.cleanup = AsyncMock(side_effect=ValueError("Cleanup error"))
        updater = MetadataStoreAutoUpdater(metadata_store=mock_store)
        updater.init_manager = MagicMock()
        updater.init_manager.cleanup = AsyncMock()

        with patch("src.common.metadata_store_auto_updater.logger") as mock_logger:
            await updater.stop()

        mock_logger.warning.assert_called()
        # Verify it completed without raising
        assert updater._shutdown_requested is True

    @pytest.mark.asyncio
    async def test_stop_logs_warning_on_task_timeout(self) -> None:
        """Logs warning when task does not complete within timeout."""
        mock_store = MagicMock()
        mock_store.cleanup = AsyncMock()
        updater = MetadataStoreAutoUpdater(metadata_store=mock_store)
        updater.init_manager = MagicMock()
        updater.init_manager.cleanup = AsyncMock()

        mock_task = MagicMock()
        mock_task.done.return_value = False
        mock_task.cancel = MagicMock()
        mock_task.get_name.return_value = "test_task"

        async def wait_side_effect(task, timeout):
            raise asyncio.TimeoutError()

        updater._listener_task = mock_task

        with patch("asyncio.wait_for", side_effect=wait_side_effect):
            with patch("src.common.metadata_store_auto_updater.logger") as mock_logger:
                await updater.stop()

        mock_logger.warning.assert_called()
        assert "did not complete within timeout" in str(mock_logger.warning.call_args_list)
