"""Keyspace event listener for MetadataStore Auto-Updater"""

import logging
from typing import Dict

from src.common.redis_protocol.typing import RedisClient

from .keyspace_listener_helpers import EventHandler, PubsubManager, ServiceExtractor

logger = logging.getLogger(__name__)


class KeyspaceListener:
    """Listens for Redis keyspace notifications and queues updates"""

    def __init__(self, pubsub_client: RedisClient, pending_updates: Dict, batch_lock):
        self.pubsub_client = pubsub_client
        self.pending_updates = pending_updates
        self.batch_lock = batch_lock

        # Initialize helpers
        self._service_extractor = ServiceExtractor()
        self._event_handler = EventHandler(pending_updates, batch_lock, self._service_extractor)
        self._pubsub_manager = PubsubManager(pubsub_client, self._event_handler)

    async def listen(self):
        """Listen for keyspace notifications on history:* keys with retry logic"""
        await self._pubsub_manager.listen_with_retry()

    def request_shutdown(self):
        """Request shutdown of listener"""
        self._pubsub_manager.request_shutdown()
