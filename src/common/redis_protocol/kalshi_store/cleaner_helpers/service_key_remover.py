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
        """
        Remove all Redis keys for this service's namespace (e.g., kalshi:ws:* or kalshi:rest:*)
        and clear subscription tracking for this service
        """
        try:
            pattern = f"kalshi:{self.service_prefix}:*"
            redis = await self._get_redis()
            keys = await redis.keys(pattern)

            # Also get subscription tracking entries for this service
            redis = await self._get_redis()
            subscriptions = await redis.hgetall(self.subscriptions_key)
            subscription_keys_to_remove = []
            prefix = f"{self.service_prefix}:"
            for key in subscriptions.keys():
                normalized_key = key.decode("utf-8") if isinstance(key, bytes) else key
                if isinstance(normalized_key, str) and normalized_key.startswith(prefix):
                    subscription_keys_to_remove.append(key)

            total_operations = len(keys) + len(subscription_keys_to_remove)
            if total_operations == 0:
                logger.info(f"No Kalshi keys or subscriptions to remove for service_prefix={self.service_prefix}")
            else:
                logger.info(
                    f"Removing {len(keys)} Kalshi keys and {len(subscription_keys_to_remove)} subscription entries for service_prefix={self.service_prefix} from Redis"
                )

                redis = await self._get_redis()
                pipe = redis.pipeline()

                # Remove service-specific keys
                for key in keys:
                    pipe.delete(key)

                # Remove subscription tracking entries for this service
                for subscription_key in subscription_keys_to_remove:
                    pipe.hdel(self.subscriptions_key, subscription_key)

                await pipe.execute()

                logger.info(
                    f"Successfully removed all Kalshi keys and subscription entries for service_prefix={self.service_prefix} from Redis"
                )

            # Always clear subscription IDs hash for this service
            redis = await self._get_redis()
            deleted = await redis.delete(self.subscription_ids_key)
            if deleted:
                logger.info(f"Cleared subscription IDs hash {self.subscription_ids_key}")
        except REDIS_ERRORS as exc:  # Expected exception, returning default value  # policy_guard: allow-silent-handler
            logger.error(
                "Error removing all Kalshi keys and subscriptions for service_prefix=%s: %s",
                self.service_prefix,
                exc,
                exc_info=True,
            )
            return False
        else:
            return True
