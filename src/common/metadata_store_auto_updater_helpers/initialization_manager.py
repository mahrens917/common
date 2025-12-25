"""Initialization management for MetadataStore Auto-Updater"""

import asyncio
import logging
from typing import Any, Optional

from common.exceptions import DataError
from common.redis_protocol.connection import perform_redis_health_check
from common.redis_protocol.typing import RedisClient, ensure_awaitable
from common.redis_utils import get_redis_connection

logger = logging.getLogger(__name__)

REDIS_ERRORS = (
    Exception,  # Catch-all for Redis errors
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
)
POOL_ERRORS = REDIS_ERRORS + (RuntimeError,)


class InitializationManager:
    """Manages Redis connection initialization and health checks"""

    redis_client: Optional[RedisClient]
    pubsub_client: Optional[RedisClient]

    def __init__(self) -> None:
        self.redis_client: Optional[RedisClient] = None
        self.pubsub_client: Optional[RedisClient] = None

    async def initialize(self, metadata_store):
        """Initialize Redis connections and enable keyspace notifications with proper readiness checks"""
        await self._ensure_redis_pool_ready()

        if self.redis_client is None:
            redis_result: Any = await get_redis_connection()
            if redis_result is None:
                raise DataError("Failed to initialize redis client")
            self.redis_client = redis_result

        if self.pubsub_client is None:
            pubsub_result: Any = await get_redis_connection()
            if pubsub_result is None:
                raise DataError("Failed to initialize pubsub client")
            self.pubsub_client = pubsub_result

        await metadata_store.initialize()

        # Enable keyspace notifications for all commands on all keys
        if self.redis_client is None:
            raise DataError("Redis client not initialized")
        await ensure_awaitable(self.redis_client.config_set("notify-keyspace-events", "KEA"))

        logger.info("MetadataStore auto-updater initialized with keyspace notifications enabled")

    async def _ensure_redis_pool_ready(self, max_retries: int = 5, base_delay: float = 1.0):
        """Ensure Redis pool is ready with exponential backoff retry"""
        for attempt in range(max_retries):
            try:
                if await perform_redis_health_check():
                    logger.info(f"Redis pool ready after {attempt + 1} attempt(s)")
                    return
                else:
                    logger.warning(f"Redis health check failed on attempt {attempt + 1}")
            except POOL_ERRORS as exc:  # Expected exception in operation  # policy_guard: allow-silent-handler
                logger.warning(
                    "Redis pool readiness check failed on attempt %s: %s",
                    attempt + 1,
                    exc,
                    exc_info=True,
                )

            if attempt < max_retries - 1:
                delay = base_delay * (2**attempt)
                logger.info(f"Waiting {delay:.1f}s before retry...")
                await asyncio.sleep(delay)

        raise ConnectionError(f"Redis pool not ready after {max_retries} attempts")

    async def cleanup(self):
        """Clean up Redis connections"""
        if self.pubsub_client:
            client = self.pubsub_client
            self.pubsub_client = None
            try:
                await asyncio.wait_for(ensure_awaitable(client.aclose()), timeout=3.0)
            except (
                asyncio.TimeoutError,
                ConnectionError,
                OSError,
                RuntimeError,
                AttributeError,
            ):  # Transient network/connection failure  # policy_guard: allow-silent-handler
                logger.warning("Failed to close pubsub client", exc_info=True)

        if self.redis_client:
            client = self.redis_client
            self.redis_client = None
            try:
                await asyncio.wait_for(ensure_awaitable(client.aclose()), timeout=3.0)
            except (
                asyncio.TimeoutError,
                ConnectionError,
                OSError,
                RuntimeError,
                AttributeError,
            ):  # Transient network/connection failure  # policy_guard: allow-silent-handler
                logger.warning("Failed to close redis client", exc_info=True)
