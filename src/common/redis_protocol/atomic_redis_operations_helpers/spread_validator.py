"""
Spread validator for Redis market data.

Validates bid/ask spreads to detect race conditions and data corruption.
"""

import logging
from typing import Any, Mapping

logger = logging.getLogger(__name__)

# Spread validation enabled by default
SPREAD_VALIDATION_ENABLED = True


class RedisDataValidationError(RuntimeError):
    """Raised when Redis market data cannot be validated after retries."""


class SpreadValidator:
    """Validates bid/ask spreads in market data."""

    def __init__(self, max_retries: int):
        """
        Initialize spread validator.

        Args:
            max_retries: Maximum number of retry attempts (for logging)
        """
        self.max_retries = max_retries
        self.logger = logger

    def validate_bid_ask_spread(
        self, converted_data: Mapping[str, Any], store_key: str, attempt_index: int
    ) -> None:
        """
        Validate bid/ask spread to detect race conditions.

        Args:
            converted_data: Converted market data
            store_key: Redis key (for error messages)
            attempt_index: Current retry attempt (for logging)

        Raises:
            RedisDataValidationError: If spread is invalid
        """
        if not SPREAD_VALIDATION_ENABLED:
            return
        if "best_bid" not in converted_data or "best_ask" not in converted_data:
            return

        try:
            bid = float(converted_data["best_bid"])
            ask = float(converted_data["best_ask"])
        except (ValueError, TypeError) as exc:
            message = f"Error validating spread for key {store_key}"
            self.logger.warning("%s, attempt %s/%s", message, attempt_index + 1, self.max_retries)
            raise RedisDataValidationError(message) from exc

        # Check for inverted spread (bid > ask)
        if bid > ask:
            message = (
                f"Invalid spread detected in key {store_key}: bid={bid} > ask={ask}. "
                "This indicates race condition or data corruption."
            )
            self.logger.warning(
                "🔍 ATOMIC_OPS_DIAGNOSTIC: %s, attempt %s/%s",
                message,
                attempt_index + 1,
                self.max_retries,
            )
            raise RedisDataValidationError(message)

        # Check for non-positive prices
        if bid <= 0 or ask <= 0:
            message = (
                f"Invalid prices in key {store_key}: bid={bid}, ask={ask} "
                "(prices must be positive)"
            )
            self.logger.warning("%s, attempt %s/%s", message, attempt_index + 1, self.max_retries)
            raise RedisDataValidationError(message)
