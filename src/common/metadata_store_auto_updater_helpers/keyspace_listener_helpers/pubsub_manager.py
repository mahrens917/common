"""Pub/sub connection and retry management"""

import asyncio
import logging

from common.connection_manager_helpers.shutdown_mixin import ShutdownRequestMixin
from common.redis_protocol.connection import perform_redis_health_check
from common.redis_protocol.typing import RedisClient, ensure_awaitable

logger = logging.getLogger(__name__)

DEFAULT_KEYSPACE_LISTENER_MAX_RETRIES = 5

REDIS_ERRORS = (
    Exception,  # Catch-all for Redis errors
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
)


class PubsubManager(ShutdownRequestMixin):
    """Manages Redis pub/sub connection with retry logic"""

    def __init__(self, pubsub_client: RedisClient, event_handler):
        """
        Initialize pub/sub manager

        Args:
            pubsub_client: Redis client for pub/sub
            event_handler: EventHandler instance
        """
        self.pubsub_client = pubsub_client
        self.event_handler = event_handler
        self._shutdown_requested = False

    async def listen_with_retry(self):
        """
        Listen for keyspace notifications on history:* keys with retry logic

        Retries up to DEFAULT_KEYSPACE_LISTENER_MAX_RETRIES times with exponential backoff.
        """
        max_retries = DEFAULT_KEYSPACE_LISTENER_MAX_RETRIES
        base_delay = 1.0
        retry_count = 0

        while not self._shutdown_requested and retry_count < max_retries:
            try:
                # Verify Redis health before attempting connection
                await self._verify_redis_health()

                # Start listening to keyspace notifications
                await self._run_listen_loop()

                # Clean exit - break the retry loop
                break

            except asyncio.CancelledError:
                # Task cancellation requested during shutdown
                logger.info("Keyspace listener cancelled")
                raise
            except REDIS_ERRORS as exc:  # Expected exception in operation  # policy_guard: allow-silent-handler
                # Handle Redis errors with retry logic
                retry_count = await self._handle_redis_error(exc, retry_count, max_retries, base_delay)

    async def _verify_redis_health(self):
        """Verify Redis is healthy before connecting."""
        if not await perform_redis_health_check():
            raise ConnectionError("Redis health check failed")

    async def _run_listen_loop(self):
        """Run the main listen loop for keyspace notifications."""
        pubsub = self.pubsub_client.pubsub()
        await ensure_awaitable(pubsub.psubscribe("__keyspace@0__:history:*"))

        logger.info("Started listening for keyspace notifications on history:* keys")

        try:
            async for message in pubsub.listen():
                if self._shutdown_requested:
                    break
                if message["type"] == "pmessage":
                    await self.event_handler.handle_keyspace_event(message)
        finally:
            await ensure_awaitable(pubsub.close())

    async def _handle_redis_error(self, exc: Exception, retry_count: int, max_retries: int, base_delay: float) -> int:
        """Handle Redis error with retry logic."""
        retry_count += 1
        logger.error(
            "Error in keyspace listener (attempt %s/%s): %s",
            retry_count,
            max_retries,
            exc,
            exc_info=True,
        )

        if retry_count >= max_retries:
            logger.error("Max retries exceeded for keyspace listener, giving up")
            return retry_count

        if not self._shutdown_requested:
            delay = base_delay * (2 ** (retry_count - 1))
            logger.info(f"Retrying keyspace listener in {delay:.1f}s...")
            await asyncio.sleep(delay)

        return retry_count
