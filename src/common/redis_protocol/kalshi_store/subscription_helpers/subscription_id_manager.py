"""
Subscription ID management for KalshiSubscriptionTracker
"""

import logging
from typing import Any, Dict, Sequence

from common.truthy import pick_if

from ...error_types import REDIS_ERRORS
from ...typing import ensure_awaitable

logger = logging.getLogger(__name__)


class SubscriptionIdManager:
    """Manages subscription IDs for Kalshi WebSocket"""

    def __init__(self, redis_getter, subscription_ids_key: str, service_prefix: str):
        self._get_redis = redis_getter
        self.subscription_ids_key = subscription_ids_key
        self.service_prefix = service_prefix

    async def record_subscription_ids(self, subscriptions: Dict[str, Any]) -> None:
        """Persist a mapping of market tickers to subscription IDs."""
        if not subscriptions:
            return
        redis = await self._get_redis()
        payload: Dict[str, str] = {}
        prefix = pick_if(self.service_prefix, lambda: f"{self.service_prefix}:", lambda: "")
        for market, sub_id in subscriptions.items():
            if sub_id is None:
                continue
            try:
                payload[f"{prefix}{market}"] = str(sub_id)
            except (TypeError, ValueError):  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
                logger.debug(
                    "Skipping subscription id for %s due to serialization failure",
                    market,
                    exc_info=True,
                )
        if not payload:
            return
        try:
            await redis.hset(self.subscription_ids_key, mapping=payload)
        except REDIS_ERRORS as exc:
            logger.error("Error recording subscription ids: %s", exc, exc_info=True)
            raise

    async def fetch_subscription_ids(self, markets: Sequence[str]) -> Dict[str, str]:
        """Retrieve subscription IDs for the provided markets."""
        if not markets:
            return {}

        redis = await self._get_redis()
        prefix = pick_if(self.service_prefix, lambda: f"{self.service_prefix}:", lambda: "")
        field_names = [f"{prefix}{market}" for market in markets]

        try:
            raw_values = await ensure_awaitable(redis.hmget(self.subscription_ids_key, field_names))
        except REDIS_ERRORS as exc:
            logger.error("Error fetching subscription ids: %s", exc, exc_info=True)
            raise

        recovered: Dict[str, str] = {}
        for market, value in zip(markets, raw_values):
            if value is None:
                continue
            if isinstance(value, bytes):
                value = value.decode("utf-8", "ignore")
            recovered[market] = str(value)
        return recovered

    async def clear_subscription_ids(self, markets: Sequence[str]) -> None:
        """Delete subscription IDs for the specified markets."""
        if not markets:
            return
        redis = await self._get_redis()
        prefix = pick_if(self.service_prefix, lambda: f"{self.service_prefix}:", lambda: "")
        try:
            await redis.hdel(
                self.subscription_ids_key,
                *(f"{prefix}{market}" for market in markets),
            )
        except REDIS_ERRORS as exc:
            logger.error("Error clearing subscription ids: %s", exc, exc_info=True)
            raise
