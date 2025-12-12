"""
Validation utilities for write operations.

This module handles validation and formatting of data before Redis writes.
"""

import logging
import math
from typing import Any, Optional

from redis.asyncio import Redis

from ...typing import ensure_awaitable

logger = logging.getLogger(__name__)


class ValidationWriter:
    """Handles validation and formatting for write operations."""

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

    @staticmethod
    def format_probability_value(value: Any) -> str:
        """
        Format probability value for Redis storage.

        Args:
            value: Value to format (must be float-compatible)

        Returns:
            Formatted string representation

        Raises:
            ValueError: If value is not float-compatible or not finite
        """
        try:
            numeric = float(value)
        except (TypeError, ValueError) as exc:  # policy_guard: allow-silent-handler
            raise TypeError(f"Probability value must be float-compatible, got {value}") from exc

        if not math.isfinite(numeric):
            raise TypeError(f"Probability value must be finite, got {numeric}")

        formatted = f"{numeric:.10f}"
        if "." in formatted:
            formatted = formatted.rstrip("0").rstrip(".")
        if not formatted:
            return "0"
        return formatted
