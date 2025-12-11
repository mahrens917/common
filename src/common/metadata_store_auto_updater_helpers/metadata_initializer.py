"""Metadata initialization from existing Redis keys"""

import logging
from collections import defaultdict

from common.redis_protocol.config import HISTORY_KEY_PREFIX
from common.redis_protocol.typing import RedisClient, ensure_awaitable

from .service_name_extractor import ServiceNameExtractor

logger = logging.getLogger(__name__)

REDIS_ERRORS = (Exception,)  # Catch-all for Redis errors


class MetadataInitializer:
    """Initializes metadata from existing history keys on startup"""

    def __init__(self, metadata_store, redis_client: RedisClient):
        self.metadata_store = metadata_store
        self.redis_client = redis_client
        self._service_name_extractor = ServiceNameExtractor()

    async def initialize_from_existing_keys(self):
        """Initialize metadata from existing history:* keys on startup"""
        try:
            logger.info("Initializing MetadataStore from existing history keys")

            pattern = f"{HISTORY_KEY_PREFIX}*"
            redis_client = self.redis_client
            keys = await ensure_awaitable(redis_client.keys(pattern))

            service_counts = defaultdict(int)

            for key in keys:
                if isinstance(key, bytes):
                    key = key.decode()

                service_name = self._service_name_extractor.extract_service_name(key)
                if not service_name:
                    continue

                if not await self._ensure_hash_history_key(key):
                    logger.warning(
                        "Skipping history key %s during initialization after failed normalization",
                        key,
                    )
                    continue

                try:
                    count = await ensure_awaitable(redis_client.hlen(key))
                    service_counts[service_name] += count

                except REDIS_ERRORS as exc:
                    logger.warning("Error counting entries in %s: %s", key, exc, exc_info=True)
                    continue

            # Initialize metadata store with counts
            for service_name, count in service_counts.items():
                await self.metadata_store.initialize_service_count(service_name, count)

            logger.info(f"Initialized metadata for {len(service_counts)} services: {dict(service_counts)}")

        except REDIS_ERRORS as exc:
            logger.error("Error initializing metadata from existing keys: %s", exc, exc_info=True)

    async def _ensure_hash_history_key(self, key: str) -> bool:
        """Ensure the given Redis history key uses the expected hash structure"""
        client = self.redis_client
        try:
            key_type = await ensure_awaitable(client.type(key))
            if isinstance(key_type, bytes):
                key_type = key_type.decode()

            if key_type in ("none", "hash"):
                return True

            logger.error(
                "History key %s has unsupported Redis type '%s'; manual cleanup required",
                key,
                key_type,
            )

        except REDIS_ERRORS as exc:
            logger.error("Failed to normalize history key %s: %s", key, exc, exc_info=True)
            return False

        return False
