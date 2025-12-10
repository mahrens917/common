"""Batch processing for MetadataStore Auto-Updater"""

import asyncio
import logging
from typing import Dict

from common.connection_manager_helpers.shutdown_mixin import ShutdownRequestMixin

logger = logging.getLogger(__name__)

REDIS_ERRORS = (Exception,)  # Catch-all for Redis errors


class BatchProcessor(ShutdownRequestMixin):
    """Processes batched updates to MetadataStore"""

    def __init__(
        self, metadata_store, pending_updates: Dict, batch_lock, batch_interval_seconds: float = 1.0
    ):
        self.metadata_store = metadata_store
        self.pending_updates = pending_updates
        self.batch_lock = batch_lock
        self.batch_interval_seconds = batch_interval_seconds
        self._shutdown_requested = False

    async def run(self):
        """Process batched updates every second"""
        try:
            while not self._shutdown_requested:
                await asyncio.sleep(self.batch_interval_seconds)

                # Get pending updates atomically
                async with self.batch_lock:
                    updates_to_process = dict(self.pending_updates)
                    self.pending_updates.clear()

                # Process updates
                if updates_to_process:
                    await self._process_batched_updates(updates_to_process)

        except asyncio.CancelledError:
            logger.info("Batch processor cancelled")
            raise
        except REDIS_ERRORS as exc:
            logger.error("Error in batch processor: %s", exc, exc_info=True)

    async def _process_batched_updates(self, updates: Dict[str, int]):
        """Process a batch of pending updates"""
        try:
            for service_name, count in updates.items():
                await self.metadata_store.increment_service_count(service_name, count)

            total_updates = sum(updates.values())
            logger.debug(f"Processed {total_updates} batched updates: {dict(updates)}")

        except REDIS_ERRORS as exc:
            logger.error("Error processing batched updates: %s", exc, exc_info=True)
