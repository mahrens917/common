"""Time window updates for MetadataStore Auto-Updater"""

import asyncio
import logging

from common.connection_manager_helpers.shutdown_mixin import ShutdownRequestMixin
from common.redis_protocol.typing import RedisClient

from .time_window_updater_helpers import ServiceUpdater

logger = logging.getLogger(__name__)

REDIS_ERRORS = (Exception,)  # Catch-all for Redis errors


class TimeWindowUpdater(ShutdownRequestMixin):
    """Updates time-windowed counts for services"""

    def __init__(self, metadata_store, redis_client: RedisClient):
        self.metadata_store = metadata_store
        self.redis_client = redis_client
        self._shutdown_requested = False
        self._service_updater = ServiceUpdater(metadata_store, redis_client)

    async def run(self):
        """Update time-windowed counts every minute"""
        try:
            while not self._shutdown_requested:
                await asyncio.sleep(60)
                await self._update_all_time_windows()

        except asyncio.CancelledError:  # policy_guard: allow-silent-handler
            logger.info("Time window updater cancelled")
            raise
        except REDIS_ERRORS as exc:  # policy_guard: allow-silent-handler
            logger.error("Error in time window updater: %s", exc, exc_info=True)

    async def _update_all_time_windows(self):
        """Update time-windowed counts for all services"""
        try:
            services = await self.metadata_store.get_all_services()
            for service_name in services:
                await self._service_updater.update_service_time_windows(service_name)

        except REDIS_ERRORS as exc:  # policy_guard: allow-silent-handler
            logger.error("Error updating time windows: %s", exc, exc_info=True)
