"""Validation helpers for trade records."""

from typing import Any, Dict

from .codec_helpers import validators


class TradeRecordValidator:
    """Validates trade record fields."""

    @staticmethod
    def validate_required_fields(data: Dict[str, Any]) -> None:
        """Validate presence of all required fields."""
        validators.validate_required_fields(data)

    @staticmethod
    def validate_trade_metadata(data: Dict[str, Any]) -> None:
        """Validate trade rule and reason fields."""
        validators.validate_trade_metadata(data)

    @staticmethod
    def validate_weather_fields(data: Dict[str, Any]) -> None:
        """Validate weather-specific fields if market category is weather."""
        validators.validate_weather_fields(data)
