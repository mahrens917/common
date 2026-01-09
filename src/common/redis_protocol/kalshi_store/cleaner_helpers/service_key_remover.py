"""
Service key removal operations for KalshiMarketCleaner
"""

import logging

from ...error_types import REDIS_ERRORS

logger = logging.getLogger(__name__)


class ServiceKeyRemover:
    """Handles removal of service-specific keys"""

    def __init__(
        self,
        redis_getter,
        subscriptions_key: str,
        service_prefix: str,
        subscription_ids_key: str,
    ):
        """
        Initialize service key remover

        Args:
            redis_getter: Async function that returns Redis client
            subscriptions_key: Redis key for subscriptions hash
            service_prefix: Service prefix (e.g., 'rest' or 'ws')
            subscription_ids_key: Redis key for subscription IDs hash
        """
        self._get_redis = redis_getter
        self.subscriptions_key = subscriptions_key
        self.service_prefix = service_prefix
        self.subscription_ids_key = subscription_ids_key

    async def remove_service_keys(self) -> bool:
        """Remove all Redis keys for this service's namespace and clear subscription tracking."""
        try:
            redis = await self._get_redis()
            keys = await redis.keys(f"kalshi:{self.service_prefix}:*")
            subscription_keys = await self._get_subscription_keys_to_remove(redis)
            await self._execute_removal(keys, subscription_keys)
            await self._clear_subscription_ids()
        except REDIS_ERRORS as exc:  # policy_guard: allow-silent-handler
            logger.error("Error removing Kalshi keys for service_prefix=%s: %s", self.service_prefix, exc, exc_info=True)
            return False
        else:
            return True

    async def _get_subscription_keys_to_remove(self, redis) -> list:
        """Get subscription keys that match this service prefix."""
        subscriptions = await redis.hgetall(self.subscriptions_key)
        prefix = f"{self.service_prefix}:"
        result = []
        for key in subscriptions.keys():
            normalized = key.decode("utf-8") if isinstance(key, bytes) else key
            if isinstance(normalized, str) and normalized.startswith(prefix):
                result.append(key)
        return result

    async def _execute_removal(self, keys: list, subscription_keys: list) -> None:
        """Execute removal of keys and subscription entries via pipeline."""
        total = len(keys) + len(subscription_keys)
        if total == 0:
            logger.info(f"No Kalshi keys or subscriptions to remove for service_prefix={self.service_prefix}")
            return

        logger.info(f"Removing {len(keys)} keys and {len(subscription_keys)} subscriptions for {self.service_prefix}")
        redis = await self._get_redis()
        pipe = redis.pipeline()
        for key in keys:
            pipe.delete(key)
        for sub_key in subscription_keys:
            pipe.hdel(self.subscriptions_key, sub_key)
        await pipe.execute()
        logger.info(f"Successfully removed Kalshi keys for service_prefix={self.service_prefix}")

    async def _clear_subscription_ids(self) -> None:
        """Clear the subscription IDs hash for this service."""
        redis = await self._get_redis()
        deleted = await redis.delete(self.subscription_ids_key)
        if deleted:
            logger.info(f"Cleared subscription IDs hash {self.subscription_ids_key}")
