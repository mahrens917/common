"""
MetadataStore Auto-Updater via Redis Keyspace Notifications

Automatically maintains MetadataStore by listening for changes to history:* keys.
Eliminates the need for services to explicitly call record_service_message().
"""

import asyncio
import logging
from collections import defaultdict
from typing import Optional

from common.metadata_store import MetadataStore
from common.metadata_store_auto_updater_helpers import (
    BatchProcessor,
    InitializationManager,
    KeyspaceListener,
    MetadataInitializer,
    TimeWindowUpdater,
)
from common.truthy import pick_if

logger = logging.getLogger(__name__)

_UNKNOWN_TASK_NAME = "unknown"


class MetadataStoreAutoUpdater:
    """Automatically updates MetadataStore by listening for Redis keyspace notifications."""

    def __init__(self, metadata_store: Optional[MetadataStore] = None):
        self.metadata_store = metadata_store or MetadataStore()
        self.batch_interval_seconds = 1.0
        self.pending_updates = defaultdict(int)
        self._batch_lock = asyncio.Lock()
        self._listener_task: Optional[asyncio.Task] = None
        self._batch_processor_task: Optional[asyncio.Task] = None
        self._time_window_updater_task: Optional[asyncio.Task] = None
        self._shutdown_requested = False
        self.init_manager = InitializationManager()
        self.keyspace_listener: Optional[KeyspaceListener] = None
        self.batch_processor: Optional[BatchProcessor] = None
        self.time_window_updater: Optional[TimeWindowUpdater] = None
        self.metadata_initializer: Optional[MetadataInitializer] = None

    async def initialize(self) -> None:
        await self.init_manager.initialize(self.metadata_store)
        pubsub_client = self.init_manager.pubsub_client
        assert pubsub_client is not None
        redis_client = self.init_manager.redis_client
        assert redis_client is not None

        self.keyspace_listener = KeyspaceListener(pubsub_client, self.pending_updates, self._batch_lock)
        self.batch_processor = BatchProcessor(self.metadata_store, self.pending_updates, self._batch_lock, self.batch_interval_seconds)
        self.time_window_updater = TimeWindowUpdater(self.metadata_store, redis_client)
        self.metadata_initializer = MetadataInitializer(self.metadata_store, redis_client)

    async def start(self) -> None:
        if self._listener_task is not None:
            logger.warning("MetadataStore auto-updater already started")
            return
        await self.initialize()
        metadata_initializer = self.metadata_initializer
        assert metadata_initializer is not None
        await metadata_initializer.initialize_from_existing_keys()
        logger.info("Starting MetadataStore auto-updater background tasks")
        keyspace_listener = self.keyspace_listener
        batch_processor = self.batch_processor
        time_window_updater = self.time_window_updater
        assert keyspace_listener is not None
        assert batch_processor is not None
        assert time_window_updater is not None
        self._listener_task = asyncio.create_task(keyspace_listener.listen())
        self._batch_processor_task = asyncio.create_task(batch_processor.run())
        self._time_window_updater_task = asyncio.create_task(time_window_updater.run())

    async def stop(self) -> None:
        logger.info("Stopping MetadataStore auto-updater")
        self._shutdown_requested = True
        self._request_component_shutdown()
        await self._cancel_background_tasks()
        await self.init_manager.cleanup()
        await self._cleanup_metadata_store()
        logger.info("MetadataStore auto-updater stopped")

    def _request_component_shutdown(self) -> None:
        for component in (self.keyspace_listener, self.batch_processor, self.time_window_updater):
            if component:
                component.request_shutdown()

    async def _cancel_background_tasks(self) -> None:
        tasks = (self._listener_task, self._batch_processor_task, self._time_window_updater_task)
        for task in tasks:
            await self._cancel_task(task)

    async def _cancel_task(self, task: asyncio.Task | None) -> None:
        if not task or task.done():
            return
        task.cancel()
        try:
            await asyncio.wait_for(task, timeout=5.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):  # policy_guard: allow-silent-handler
            logger.warning("Task %s did not complete within timeout", self._resolve_task_name(task))

    @staticmethod
    def _resolve_task_name(task: asyncio.Task | None) -> str:
        if task is None:
            return _UNKNOWN_TASK_NAME
        if hasattr(task, "get_name"):
            return task.get_name()
        return _UNKNOWN_TASK_NAME

    async def _cleanup_metadata_store(self) -> None:
        try:
            await self.metadata_store.cleanup()
        except (RuntimeError, OSError, ValueError, AttributeError, ConnectionError) as exc:  # policy_guard: allow-silent-handler
            logger.warning("Metadata store cleanup failed during stop: %s", exc)
