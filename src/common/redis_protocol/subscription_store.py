"""
Reliable subscription management with atomic operations
"""

import logging
from typing import Dict, Optional

from . import messages
from .subscription_store_helpers import (
    ChannelResolver,
    SubscriptionOperations,
    SubscriptionRetrieval,
    SubscriptionStoreConnectionManager,
)
from .typing import RedisClient

logger = logging.getLogger(__name__)


class _SubscriptionChannelAccessors:
    """Resolve Redis channel and hash names based on service type."""

    _channel_resolver: ChannelResolver

    def _get_subscription_channel(self) -> str:
        return self._channel_resolver.get_subscription_channel()

    def _get_subscription_hash(self) -> str:
        return self._channel_resolver.get_subscription_hash()


class _SubscriptionConnectionAccessors:
    """Expose accessors for the connection manager."""

    _connection_manager: SubscriptionStoreConnectionManager

    @property
    def redis(self) -> Optional[RedisClient]:
        return self._connection_manager.redis

    @redis.setter
    def redis(self, value: Optional[RedisClient]):
        self._connection_manager.redis = value

    @property
    def pubsub(self):
        return self._connection_manager.pubsub

    @property
    def pool(self):
        return self._connection_manager.pool

    @property
    def initialized(self) -> bool:
        return self._connection_manager.initialized

    @initialized.setter
    def initialized(self, value: bool):
        self._connection_manager.initialized = value

    @property
    def _initialized(self) -> bool:
        return self._connection_manager.initialized

    @_initialized.setter
    def _initialized(self, value: bool):
        self._connection_manager.initialized = value


class SubscriptionStore(_SubscriptionConnectionAccessors, _SubscriptionChannelAccessors):
    """Handles subscription management with efficient Redis operations"""

    def __init__(self, service_type: str = "deribit", pool=None):
        """Initialize with service type and optional connection pool

        Args:
            service_type: Service type ('deribit' or 'kalshi') to determine subscription channel
            pool: Optional Redis connection pool
        """
        self.service_type = service_type
        self._channel_resolver = ChannelResolver(service_type)
        self._connection_manager = SubscriptionStoreConnectionManager(pool)
        self._connection_manager.set_parent(self)
        self._operations = SubscriptionOperations()
        self._retrieval = SubscriptionRetrieval()

    async def _get_redis(self) -> RedisClient:
        """Get Redis connection, ensuring it's properly initialized"""
        return await self._connection_manager.get_redis()

    async def __aenter__(self):
        """Setup Redis connection from pool"""
        await self._connection_manager.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup resources"""
        await self._connection_manager.cleanup()

    async def add_subscription(self, update: messages.SubscriptionUpdate) -> bool:
        """Add subscription to Redis using unified key structure"""
        redis = await self._get_redis()
        return await self._operations.add_subscription(redis, self._get_subscription_hash(), self._get_subscription_channel(), update)

    async def remove_subscription(self, update: messages.SubscriptionUpdate) -> bool:
        """Remove subscription from Redis using unified key structure"""
        redis = await self._get_redis()
        return await self._operations.remove_subscription(redis, self._get_subscription_hash(), self._get_subscription_channel(), update)

    async def get_active_subscriptions(self) -> Dict[str, Dict[str, str]]:
        """Get all active subscriptions from Redis grouped by type"""
        try:
            redis = await self._get_redis()
        except (  # policy_guard: allow-silent-handler
            RuntimeError,
            ConnectionError,
            AttributeError,
        ) as exc:  # pragma: no cover - defensive guard
            logger.error("Failed to acquire Redis for subscription listing: %s", exc, exc_info=True)
            return {}
        return await self._retrieval.get_active_subscriptions(redis, self._get_subscription_hash())

    async def verify_subscriptions(self) -> Dict[str, int]:
        """Get subscription counts from Redis"""
        try:
            redis = await self._get_redis()
        except (  # policy_guard: allow-silent-handler
            RuntimeError,
            ConnectionError,
            AttributeError,
        ) as exc:  # pragma: no cover - defensive guard
            logger.error(
                "Failed to acquire Redis for subscription verification: %s",
                exc,
                exc_info=True,
            )
            return {"instruments": 0, "price_indices": 0, "volatility_indices": 0}
        return await self._retrieval.verify_subscriptions(redis, self._get_subscription_hash())
