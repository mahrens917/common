"""Keyspace event handling logic"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


# Constants
_CONST_3 = 3


class EventHandler:
    """Handles individual keyspace notification events"""

    def __init__(self, pending_updates: Dict, batch_lock, service_extractor):
        """
        Initialize event handler

        Args:
            pending_updates: Shared dictionary for pending updates
            batch_lock: Asyncio lock for batch access
            service_extractor: ServiceExtractor instance
        """
        self.pending_updates = pending_updates
        self.batch_lock = batch_lock
        self.service_extractor = service_extractor

    async def handle_keyspace_event(self, message: Dict):
        """
        Handle a single keyspace notification event

        Args:
            message: Keyspace notification message from Redis
        """
        if not message:
            return
        try:
            channel = message["channel"].decode() if isinstance(message["channel"], bytes) else message["channel"]
            operation = message["data"].decode() if isinstance(message["data"], bytes) else message["data"]

            key_parts = channel.split(":", 2)
            if len(key_parts) < _CONST_3:
                return

            redis_key = key_parts[2]

            if operation not in ["hset", "set", "zadd"]:
                return

            service_name = self.service_extractor.extract_service_name(redis_key)
            if not service_name:
                return

            async with self.batch_lock:
                self.pending_updates[service_name] += 1

            logger.debug(f"Queued update for {service_name} (operation: {operation})")

        except (
            RuntimeError,
            ValueError,
            KeyError,
            AttributeError,
        ) as exc:  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
            logger.error("Error handling keyspace event: %s", exc, exc_info=True)
