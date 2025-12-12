"""
Subscription retrieval and verification operations.
"""

import logging
from typing import Dict, Tuple, Union

from ..error_types import REDIS_ERRORS
from ..typing import RedisClient, ensure_awaitable

logger = logging.getLogger(__name__)


class SubscriptionRetrieval:
    """Handles subscription retrieval and verification operations"""

    @staticmethod
    def _decode_text(value: Union[str, bytes]) -> str:
        if isinstance(value, bytes):
            try:
                return value.decode("utf-8")
            except UnicodeDecodeError:  # policy_guard: allow-silent-handler
                return value.decode("utf-8", errors="replace")
        return str(value)

    @staticmethod
    def _parse_typed_key(typed_key: Union[str, bytes]) -> Tuple[str, str]:
        decoded = SubscriptionRetrieval._decode_text(typed_key)
        if ":" in decoded:
            head, tail = decoded.split(":", 1)
            return head, tail
        return "", ""

    @staticmethod
    def _map_subscription_type(sub_type: str) -> str:
        if sub_type == "instrument":
            return "instruments"
        if sub_type == "price_index":
            return "price_indices"
        if sub_type == "volatility_index":
            return "volatility_indices"
        return ""

    async def get_active_subscriptions(self, redis: RedisClient, hash_key: str) -> Dict[str, Dict[str, str]]:
        try:
            all_subscriptions = await ensure_awaitable(redis.hgetall(hash_key))
            grouped: Dict[str, Dict[str, str]] = {
                "instruments": {},
                "price_indices": {},
                "volatility_indices": {},
            }
            for typed_key, channel in all_subscriptions.items():
                sub_type, name = self._parse_typed_key(typed_key)
                category = self._map_subscription_type(sub_type)
                if category:
                    grouped[category][name] = self._decode_text(channel)
        except REDIS_ERRORS as exc:  # policy_guard: allow-silent-handler
            logger.error("Failed to get active subscriptions: %s", exc, exc_info=True)
            return {}
        else:
            return grouped

    async def verify_subscriptions(self, redis: RedisClient, hash_key: str) -> Dict[str, int]:
        try:
            all_subscriptions = await ensure_awaitable(redis.hgetall(hash_key))
            counts = {"instruments": 0, "price_indices": 0, "volatility_indices": 0}
            for typed_key in all_subscriptions.keys():
                sub_type, _ = self._parse_typed_key(typed_key)
                category = self._map_subscription_type(sub_type)
                if category:
                    counts[category] += 1
            total = sum(counts.values())
            logger.info("Active subscriptions: %s", total)
        except REDIS_ERRORS as exc:  # policy_guard: allow-silent-handler
            logger.error("Count failed: %s", exc, exc_info=True)
            return {"instruments": 0, "price_indices": 0, "volatility_indices": 0}
        else:
            return counts
