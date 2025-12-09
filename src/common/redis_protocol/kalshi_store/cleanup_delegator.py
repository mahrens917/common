"""
Cleanup operations delegator for KalshiStore.

Handles market removal, key cleanup, and metadata clearing.
"""

from typing import List, Optional

from .cleaner import KalshiMarketCleaner


class CleanupDelegator:
    """Handles cleanup operations delegation."""

    def __init__(self, cleaner: KalshiMarketCleaner) -> None:
        """Initialize cleanup delegator."""
        self._cleaner = cleaner

    async def remove_market_completely(
        self,
        market_ticker: str,
        *,
        category: Optional[str] = None,
    ) -> bool:
        """Remove market completely from Redis."""
        return await self._cleaner.remove_market_completely(
            market_ticker,
            category=category,
        )

    async def remove_service_keys(self) -> bool:  # pragma: no cover - runtime cleanup path
        """Remove service-specific keys."""
        return await self._cleaner.remove_service_keys()

    async def clear_market_metadata(
        self,
        pattern: Optional[str] = None,
        *,
        chunk_size: int = 500,
        categories: Optional[List[str]] = None,
    ) -> int:
        """Clear market metadata."""
        target_pattern = pattern or "markets:kalshi:*"
        return await self._cleaner.clear_market_metadata(
            target_pattern,
            chunk_size=chunk_size,
            categories=categories,
        )

    async def remove_all_kalshi_keys(
        self,
        *,
        categories: Optional[List[str]] = None,
        exclude_analytics: bool = True,
    ) -> int:
        """Remove all Kalshi keys."""
        return await self._cleaner.remove_all_kalshi_keys(
            categories=categories,
            exclude_analytics=exclude_analytics,
        )
