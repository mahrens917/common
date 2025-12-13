"""
Validation utilities for write operations.

This module handles validation and formatting of data before Redis writes.
"""

import logging
from typing import Any, Optional

from redis.asyncio import Redis

from ...market_normalization_core import format_probability_value as _format_probability_value
from ...typing import ensure_awaitable

logger = logging.getLogger(__name__)


class ValidationWriter:
    """Handles validation and formatting for write operations."""

    format_probability_value = staticmethod(_format_probability_value)

    def __init__(self, redis_connection: Redis, logger_instance: logging.Logger):
        """
        Initialize ValidationWriter.

        Args:
            redis_connection: Active Redis connection
            logger_instance: Logger instance
        """
        self.redis = redis_connection
        self.logger = logger_instance

    async def store_optional_field(self, market_key: str, field: str, value: Optional[Any]) -> None:
        """Persist a Redis hash field only when a value exists."""
        if value is None:
            await ensure_awaitable(self.redis.hdel(market_key, field))
            return
        await ensure_awaitable(self.redis.hset(market_key, field, str(value)))
