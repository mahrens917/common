"""Pub/sub connection and retry management"""

import asyncio
import logging

from common.connection_manager_helpers.shutdown_mixin import ShutdownRequestMixin
from common.redis_protocol.connection import perform_redis_health_check
from common.redis_protocol.typing import RedisClient, ensure_awaitable

logger = logging.getLogger(__name__)

_MAX_BACKOFF_SECONDS = 60

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
        Listen for keyspace notifications on history:* keys with retry logic.

        Retries indefinitely with exponential backoff capped at _MAX_BACKOFF_SECONDS.
        Resets backoff after a successful connection.
        """
        base_delay = 1.0
        consecutive_failures = 0

        while not self._shutdown_requested:
            try:
                # Verify Redis health before attempting connection
                await self._verify_redis_health()
                consecutive_failures = 0

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
                consecutive_failures = await self._handle_redis_error(exc, consecutive_failures, base_delay)

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

    async def _handle_redis_error(self, exc: Exception, consecutive_failures: int, base_delay: float) -> int:
        """Handle Redis error with capped exponential backoff."""
        consecutive_failures += 1
        logger.error(
            "Error in keyspace listener (consecutive failure %s): %s",
            consecutive_failures,
            exc,
            exc_info=True,
        )

        if not self._shutdown_requested:
            delay = min(base_delay * (2 ** (consecutive_failures - 1)), _MAX_BACKOFF_SECONDS)
            logger.info("Retrying keyspace listener in %.1f s...", delay)
            await asyncio.sleep(delay)

        return consecutive_failures
