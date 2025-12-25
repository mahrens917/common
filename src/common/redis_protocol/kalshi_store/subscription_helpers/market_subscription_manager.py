"""
Market subscription management for KalshiSubscriptionTracker
"""

import logging
from typing import Optional, Set

from ...error_types import REDIS_ERRORS

logger = logging.getLogger(__name__)


class MarketSubscriptionManager:
    """Manages subscribed markets for Kalshi WebSocket"""

    def __init__(self, redis_getter, subscriptions_key: str, service_prefix: str):
        """
        Initialize market subscription manager

        Args:
            redis_getter: Async function that returns Redis client
            subscriptions_key: Redis key for subscriptions hash
            service_prefix: Service prefix (e.g., 'rest' or 'ws')
        """
        self._get_redis = redis_getter
        self.subscriptions_key = subscriptions_key
        self.service_prefix = service_prefix

    async def get_subscribed_markets(self) -> Set[str]:
        """
        Get set of subscribed markets

        Returns:
            Set of market tickers
        """
        try:
            redis = await self._get_redis()
            subscriptions = await redis.hgetall(self.subscriptions_key)
            markets = set()
            prefix = f"{self.service_prefix}:"
            for key, value in subscriptions.items():
                key_str = key.decode("utf-8") if isinstance(key, bytes) else key
                value_str = value.decode("utf-8") if isinstance(value, bytes) else value
                if isinstance(key_str, str) and key_str.startswith(prefix) and value_str == "1":
                    markets.add(key_str[len(prefix) :])
        except REDIS_ERRORS as exc:
            logger.error("Error getting subscribed markets: %s", exc, exc_info=True)
            raise
        else:
            return markets

    async def add_subscribed_market(self, market_ticker: str, *, category: Optional[str] = None) -> bool:
        """
        Add market to subscribed markets

        Args:
            market_ticker: Market ticker

        Returns:
            True if successful, False otherwise
        """
        try:
            subscription_key = f"{self.service_prefix}:{market_ticker}"
            redis = await self._get_redis()
            await redis.hset(self.subscriptions_key, subscription_key, "1")
        except REDIS_ERRORS as exc:
            logger.error("Error adding subscribed market %s: %s", market_ticker, exc, exc_info=True)
            raise
        else:
            return True

    async def remove_subscribed_market(self, market_ticker: str, *, category: Optional[str] = None) -> bool:
        """
        Remove market from subscribed markets

        Args:
            market_ticker: Market ticker

        Returns:
            True if successful, False otherwise
        """
        try:
            subscription_key = f"{self.service_prefix}:{market_ticker}"
            redis = await self._get_redis()
            await redis.hdel(self.subscriptions_key, subscription_key)
        except REDIS_ERRORS as exc:
            logger.error("Error removing subscribed market %s: %s", market_ticker, exc, exc_info=True)
            raise
        else:
            return True
