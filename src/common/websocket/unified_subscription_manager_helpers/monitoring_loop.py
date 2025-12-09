"""Monitoring loop for Redis subscription updates."""

import asyncio
import logging

from ...redis_protocol.error_types import REDIS_ERRORS
from .message_processor import MessageProcessor

logger = logging.getLogger(__name__)


class MonitoringLoop:
    """Manages the Redis pub/sub monitoring loop."""

    def __init__(
        self,
        service_name: str,
        subscription_channel: str,
        update_handler,
        subscription_processor,
        health_validator,
    ):
        """
        Initialize monitoring loop.

        Args:
            service_name: Name of the service
            subscription_channel: Redis channel for subscription updates
            update_handler: Handler for subscription updates
            subscription_processor: Processor for pending subscriptions
            health_validator: Validator for subscription health
        """
        self.service_name = service_name
        self.subscription_channel = subscription_channel
        self.message_processor = MessageProcessor(
            service_name, update_handler, subscription_processor, health_validator
        )

    async def run(self) -> None:
        """Monitor Redis subscription updates."""
        from src.common.redis_protocol.connection_pool_core import get_redis_client

        redis_client = await get_redis_client()

        try:
            pubsub = redis_client.pubsub()
            await pubsub.subscribe(self.subscription_channel)
            logger.info(f"Subscribed to {self.subscription_channel} channel")

            try:
                await self._listen_loop(pubsub, redis_client)
            finally:
                await self._cleanup_pubsub(pubsub)

        except REDIS_ERRORS + (ConnectionError, RuntimeError):
            logger.exception("Fatal error in %s subscription monitoring", self.service_name)
            raise
        finally:
            await self._cleanup_redis(redis_client)

    async def _listen_loop(self, pubsub, redis_client) -> None:
        """Main listening loop."""
        while True:
            try:
                async for message in pubsub.listen():
                    try:
                        await self.message_processor.process_message(message, redis_client)
                    except REDIS_ERRORS + (Exception,):
                        logger.exception(
                            "Error processing %s subscription message",
                            self.service_name,
                        )
                        continue

                    await asyncio.sleep(0.1)  # Check frequently

            except asyncio.CancelledError:
                logger.info(f"{self.service_name} subscription monitoring cancelled")
                break
            except REDIS_ERRORS + (ConnectionError, RuntimeError, ValueError):
                logger.exception(
                    "Error monitoring %s subscriptions",
                    self.service_name,
                )
                await asyncio.sleep(5)  # Longer delay for serious errors
                continue

    async def _cleanup_pubsub(self, pubsub) -> None:
        """Clean up pubsub subscription."""
        try:
            await pubsub.unsubscribe(self.subscription_channel)
        except REDIS_ERRORS + (ConnectionError, RuntimeError, ValueError):
            logger.exception("Error unsubscribing from %s channel", self.service_name)

    async def _cleanup_redis(self, redis_client) -> None:
        """Clean up Redis connection."""
        try:
            await redis_client.aclose()
        except REDIS_ERRORS:
            logger.exception("Error closing %s Redis connection", self.service_name)
