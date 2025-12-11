"""
Storage delegation for KalshiStore - Async field operations.

Extracts async storage methods from KalshiStore to reduce class size.
"""

from typing import Any, Optional

from redis.asyncio import Redis

from .writer import KalshiMarketWriter


class StorageDelegator:
    """Delegates async storage operations for optional fields."""

    def __init__(self, writer: KalshiMarketWriter) -> None:
        self._writer = writer

    async def store_optional_field(self, redis: Redis, market_key: str, field: str, value: Optional[Any]) -> None:
        """Store optional field in Redis if value is not None."""
        await self._writer.store_optional_field(redis, market_key, field, value)
