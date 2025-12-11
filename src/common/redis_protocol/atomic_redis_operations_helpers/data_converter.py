"""
Data converter for Redis market data.

Converts string values from Redis into appropriate Python types.
"""

import logging
from typing import Any, Dict, Mapping

logger = logging.getLogger(__name__)


class RedisDataValidationError(RuntimeError):
    """Raised when Redis market data cannot be validated after retries."""


class DataConverter:
    """Converts Redis string data to appropriate types."""

    def __init__(self, max_retries: int):
        """
        Initialize data converter.

        Args:
            max_retries: Maximum number of retry attempts (for logging)
        """
        self.max_retries = max_retries
        self.logger = logger

    def convert_market_payload(self, raw_data: Mapping[str, str], store_key: str, attempt_index: int) -> Dict[str, Any]:
        """
        Convert Redis string data to appropriate types.

        Args:
            raw_data: Raw string data from Redis
            store_key: Redis key (for error messages)
            attempt_index: Current retry attempt (for logging)

        Returns:
            Converted data with appropriate types

        Raises:
            RedisDataValidationError: If type conversion fails
        """
        converted: Dict[str, Any] = {}
        for field, value in raw_data.items():
            if field in {"last_update", "source_timestamp"}:
                converted[field] = value
                continue
            try:
                converted[field] = self._coerce_numeric_value(value)
            except (ValueError, TypeError) as exc:
                message = f"Failed to coerce field {field!r} for key {store_key}"
                self.logger.warning("%s, attempt %s/%s", message, attempt_index + 1, self.max_retries)
                raise RedisDataValidationError(message) from exc
        return converted

    @staticmethod
    def _coerce_numeric_value(value: Any) -> Any:
        """
        Coerce string value to numeric type if possible.

        Args:
            value: Value to coerce

        Returns:
            Float if value contains decimal, int if digits only, otherwise original
        """
        string_value = str(value)
        if "." in string_value:
            return float(string_value)
        if string_value.isdigit():
            return int(string_value)
        return value
