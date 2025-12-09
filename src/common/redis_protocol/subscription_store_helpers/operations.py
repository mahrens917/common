"""
Subscription add/remove operations.
"""

import logging

from .. import messages
from ..error_types import REDIS_ERRORS
from ..typing import RedisClient, ensure_awaitable

logger = logging.getLogger(__name__)


# Constants
_CONST_5 = 5


class SubscriptionOperations:
    """Handles subscription add/remove operations"""

    @staticmethod
    def _validate_channel(channel: str | None) -> bool:
        if channel is None or not channel.strip():
            return False
        if channel.isdigit() and len(channel) < _CONST_5:
            return False
        return True

    @staticmethod
    def _create_typed_key(update: messages.SubscriptionUpdate) -> str:
        return f"{update.subscription_type}:{update.name}"

    async def add_subscription(
        self,
        redis: RedisClient,
        hash_key: str,
        channel_key: str,
        update: messages.SubscriptionUpdate,
    ) -> bool:
        try:
            typed_key = self._create_typed_key(update)
            channel = getattr(update.metadata, "channel", None)
            if not self._validate_channel(channel):
                logger.error("Invalid channel: %s", channel)
                return False
            pipe = redis.pipeline(transaction=False)
            pipe.hset(hash_key, typed_key, channel)
            pipe.publish(channel_key, update.to_json())
            await ensure_awaitable(pipe.execute())
        except REDIS_ERRORS as exc:
            logger.error("Add failed: %s", exc, exc_info=True)
            return False
        else:
            return True

    async def remove_subscription(
        self,
        redis: RedisClient,
        hash_key: str,
        channel_key: str,
        update: messages.SubscriptionUpdate,
    ) -> bool:
        try:
            typed_key = self._create_typed_key(update)
            pipe = redis.pipeline(transaction=False)
            pipe.hdel(hash_key, typed_key)
            pipe.publish(channel_key, update.to_json())
            await ensure_awaitable(pipe.execute())
        except REDIS_ERRORS as exc:
            logger.error("Remove failed: %s", exc, exc_info=True)
            return False
        else:
            return True
