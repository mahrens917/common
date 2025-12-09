"""Key collection and deletion logic for probability store."""

import logging
from typing import List

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class KeyCollector:
    """Handles collection and deletion of probability keys."""

    async def collect_existing_probability_keys(self, redis: Redis, prefix: str) -> List[str]:
        """
        Collect all existing probability keys with given prefix.

        Args:
            redis: Redis client
            prefix: Key prefix to search for

        Returns:
            List of matching keys as strings
        """
        raw_keys = await redis.keys(f"{prefix}*")
        return [key.decode("utf-8") if isinstance(key, bytes) else str(key) for key in raw_keys]

    def queue_probability_deletes(self, pipeline, keys_to_delete: List[str]) -> None:
        """
        Queue delete operations for probability keys.

        Args:
            pipeline: Redis pipeline
            keys_to_delete: List of keys to delete
        """
        for key in keys_to_delete:
            pipeline.delete(key)
