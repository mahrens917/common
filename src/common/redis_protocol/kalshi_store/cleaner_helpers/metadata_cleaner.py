"""
Market metadata cleanup operations for KalshiMarketCleaner
"""

import logging
from typing import List

logger = logging.getLogger(__name__)


class MetadataCleaner:
    """Handles cleanup of Kalshi market metadata"""

    def __init__(self, redis_getter):
        """
        Initialize metadata cleaner

        Args:
            redis_getter: Async function that returns Redis client
        """
        self._get_redis = redis_getter

    async def clear_market_metadata(
        self,
        pattern: str = "markets:kalshi:*",
        chunk_size: int = 500,
    ) -> int:
        """Remove all Kalshi market metadata hashes that match the given pattern."""

        if chunk_size <= 0:
            raise TypeError(f"chunk_size must be positive, got {chunk_size}")

        redis = await self._get_redis()
        total_removed = 0
        batch: List[str] = []

        async for key in redis.scan_iter(match=pattern, count=chunk_size):
            batch.append(key)
            if len(batch) >= chunk_size:
                total_removed += await redis.delete(*batch)
                batch.clear()

        if batch:
            total_removed += await redis.delete(*batch)

        if total_removed:
            logger.info(
                "Removed %s Kalshi market metadata keys matching pattern '%s'",
                total_removed,
                pattern,
            )
        else:
            logger.debug(
                "No Kalshi market metadata keys matched pattern '%s' during clear_market_metadata",
                pattern,
            )

        return total_removed
