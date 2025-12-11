"""
Field validator for Redis market data.

Validates that required fields are present in fetched data.
"""

import logging
from typing import Any, Mapping, Sequence

logger = logging.getLogger(__name__)


class RedisDataValidationError(RuntimeError):
    """Raised when Redis market data cannot be validated after retries."""


class FieldValidator:
    """Validates required fields in market data."""

    def __init__(self, max_retries: int):
        """
        Initialize field validator.

        Args:
            max_retries: Maximum number of retry attempts (for logging)
        """
        self.max_retries = max_retries
        self.logger = logger

    def ensure_required_fields(
        self,
        raw_data: Mapping[str, Any],
        required_fields: Sequence[str],
        store_key: str,
        attempt_index: int,
    ) -> None:
        """
        Ensure all required fields are present in data.

        Args:
            raw_data: Data fetched from Redis
            required_fields: List of required field names
            store_key: Redis key (for error messages)
            attempt_index: Current retry attempt (for logging)

        Raises:
            RedisDataValidationError: If required fields are missing
        """
        missing_fields = [field for field in required_fields if field not in raw_data]
        if not missing_fields:
            return

        message = f"Missing required fields {missing_fields} in key {store_key}. " f"Available fields: {list(raw_data.keys())}"
        self.logger.warning(
            "🔍 ATOMIC_OPS_DIAGNOSTIC: %s, attempt %s/%s",
            message,
            attempt_index + 1,
            self.max_retries,
        )
        raise RedisDataValidationError(message)
