"""
Kalshi market cleanup operations

This module provides cleanup functionality for Kalshi market data in Redis.
"""

from __future__ import annotations

import logging
from typing import Iterable, List, Optional, Sequence, Union

from redis.asyncio import Redis

from common.exceptions import DataError
from common.redis_schema.markets import KalshiMarketCategory

from .cleaner_helpers import MarketRemover, MetadataCleaner, ServiceKeyRemover
from .connection import RedisConnectionManager

logger = logging.getLogger(__name__)


_SUBSCRIPTIONS_KEY = "kalshi:subscriptions"
_SUBSCRIBED_MARKETS_KEY = "kalshi:subscribed_markets"


def _market_key_from_ticker(market_ticker: str) -> str:
    from ...redis_schema import describe_kalshi_ticker

    return describe_kalshi_ticker(market_ticker).key


def _snapshot_key_from_ticker(market_ticker: str) -> str:
    return f"kalshi:market:{market_ticker}"


def _normalize_category_name(category: Union[str, KalshiMarketCategory]) -> str:
    if isinstance(category, KalshiMarketCategory):
        return category.value
    normalized = str(category).strip().lower()
    if not normalized:
        raise ValueError("Kalshi market category cannot be blank")
    try:
        return KalshiMarketCategory(normalized).value
    except ValueError as exc:
        raise ValueError(f"Unknown Kalshi market category '{category}'") from exc


def _metadata_patterns(
    categories: Optional[Sequence[Optional[Union[str, KalshiMarketCategory]]]],
    default_pattern: str,
) -> List[str]:
    if not categories:
        return [default_pattern]
    normalized = [
        _normalize_category_name(category) for category in categories if category is not None
    ]
    if not normalized:
        return [default_pattern]
    return [f"markets:kalshi:{category}:*" for category in normalized]


def _key_patterns(
    categories: Optional[Sequence[Optional[Union[str, KalshiMarketCategory]]]],
    exclude_analytics: bool,
) -> List[str]:
    normalized = [
        _normalize_category_name(category)
        for category in (categories or [])
        if category is not None
    ]
    if normalized:
        base_patterns = [
            pattern
            for category in normalized
            for pattern in (f"kalshi:{category}:*", f"markets:kalshi:{category}:*")
        ]
        analytics_patterns: Iterable[str] = (
            []
            if exclude_analytics
            else [f"analytics:kalshi:{category}:*" for category in normalized]
        )
    else:
        base_patterns = ["kalshi:*", "markets:kalshi:*"]
        analytics_patterns = [] if exclude_analytics else ["analytics:kalshi:*"]
    ordered_patterns = base_patterns + list(analytics_patterns)
    return list(dict.fromkeys(ordered_patterns))


class KalshiMarketCleaner:
    """Handles cleanup operations for Kalshi market data in Redis."""

    SUBSCRIPTIONS_KEY = _SUBSCRIPTIONS_KEY
    SUBSCRIBED_MARKETS_KEY = _SUBSCRIBED_MARKETS_KEY

    def __init__(
        self,
        redis: Optional[Redis] = None,
        service_prefix: Optional[str] = None,
        *,
        connection_manager: Optional[RedisConnectionManager] = None,
        subscriptions_key: Optional[str] = None,
    ) -> None:
        if service_prefix is not None and service_prefix not in ("rest", "ws"):
            raise TypeError("service_prefix must be 'rest' or 'ws' when provided")
        self.service_prefix = service_prefix
        self.logger = logger
        self._connection = (
            connection_manager
            if connection_manager is not None
            else RedisConnectionManager(logger=self.logger, redis=redis)
        )
        if subscriptions_key:
            self.SUBSCRIPTIONS_KEY = subscriptions_key
        self._market_remover = MarketRemover(
            self._get_redis,
            self.SUBSCRIPTIONS_KEY,
            _SUBSCRIBED_MARKETS_KEY,
            service_prefix or "ws",
            _market_key_from_ticker,
            _snapshot_key_from_ticker,
        )
        self._service_key_remover = ServiceKeyRemover(
            self._get_redis, self.SUBSCRIPTIONS_KEY, service_prefix or "ws"
        )
        self._metadata_cleaner = MetadataCleaner(self._get_redis)

    async def _ensure_redis_connection(self) -> bool:
        return await self._connection.ensure_redis_connection()

    async def _get_redis(self) -> Redis:
        if not await self._ensure_redis_connection():
            raise RuntimeError("Failed to establish Redis connection")
        return await self._connection.get_redis()

    async def remove_market_completely(
        self, market_ticker: str, *, category: Optional[str] = None
    ) -> bool:
        if not await self._ensure_redis_connection():
            self.logger.error(
                "Failed to ensure Redis connection for remove_market_completely %s",
                market_ticker,
            )
            return False
        return await self._market_remover.remove_market_completely(market_ticker)

    async def remove_service_keys(self) -> bool:
        if not await self._ensure_redis_connection():
            self.logger.error("Failed to ensure Redis connection for remove_service_keys")
            return False
        return await self._service_key_remover.remove_service_keys()

    async def clear_market_metadata(
        self,
        pattern: str = "markets:kalshi:*",
        chunk_size: int = 500,
        *,
        categories: Optional[Sequence[Union[str, KalshiMarketCategory]]] = None,
    ) -> int:
        if not await self._ensure_redis_connection():
            raise DataError("Failed to ensure Redis connection for clear_market_metadata")
        patterns = _metadata_patterns(categories, pattern)
        total_removed = 0
        for current_pattern in patterns:
            total_removed += await self._metadata_cleaner.clear_market_metadata(
                current_pattern, chunk_size
            )
        return total_removed

    async def remove_all_kalshi_keys(
        self,
        *,
        categories: Optional[Sequence[Union[str, KalshiMarketCategory]]] = None,
        exclude_analytics: bool = True,
    ) -> bool:
        if not await self._ensure_redis_connection():
            self.logger.error("Failed to ensure Redis connection for remove_all_kalshi_keys")
            return False
        patterns = _key_patterns(categories, exclude_analytics)
        return await self._market_remover.remove_all_kalshi_keys(patterns=patterns)


__all__ = ["KalshiMarketCleaner"]
