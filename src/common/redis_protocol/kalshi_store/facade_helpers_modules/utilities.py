"""Static utility methods."""

from typing import Any, Dict


class StaticUtilities:
    """Static utility methods for KalshiStore."""

    @staticmethod
    def normalise_hash(raw_hash: Dict[Any, Any]) -> Dict[str, Any]:
        """Convert Redis hash responses to a str-keyed dictionary."""
        from ..utils_coercion import normalise_hash as util_normalise_hash

        return util_normalise_hash(raw_hash)

    @staticmethod
    def sync_top_of_book_fields(snapshot: Dict[str, Any]) -> None:
        """Align scalar YES side fields with the JSON orderbook payload."""
        from ..utils_coercion import sync_top_of_book_fields as util_sync_top_of_book

        util_sync_top_of_book(snapshot)

    @staticmethod
    def format_probability_value(value: Any) -> str:
        """Format probability value for storage."""
        from ..utils_coercion import format_probability_value as util_format_prob

        return util_format_prob(value)

    @staticmethod
    def normalize_timestamp(value: Any) -> str | None:
        """Normalize timestamp format to ISO8601."""
        from ..metadata_helpers.timestamp_normalization import normalize_timestamp as _normalize_timestamp

        return _normalize_timestamp(value)

    @staticmethod
    def normalise_trade_timestamp(value: Any) -> str:
        """Convert Kalshi trade timestamps to ISO8601."""
        from ..utils_market import normalise_trade_timestamp as util_normalise_trade_ts

        return util_normalise_trade_ts(value)

    @staticmethod
    def coerce_mapping(candidate: Any) -> Dict[str, Any]:
        """Convert candidate to dict, returning empty dict if not a dict."""
        from ..utils_coercion import coerce_mapping as util_coerce_mapping

        return util_coerce_mapping(candidate)

    @staticmethod
    def string_or_default(value: Any, fallback_value: str = "") -> str:
        """Coerce value to string with fallback value."""
        from ..utils_coercion import string_or_default as util_string_or_default

        return util_string_or_default(value, fallback_value)

    @staticmethod
    def int_or_default(value: Any, fallback_value: int = 0) -> int:
        """Coerce value to int with fallback value."""
        from ..utils_coercion import int_or_default as util_int_or_default

        return util_int_or_default(value, fallback_value)

    @staticmethod
    def float_or_default(value: Any, fallback_value: float = 0.0) -> float:
        """Coerce value to float with fallback value."""
        from ..utils_coercion import float_or_default as util_float_or_default

        return util_float_or_default(value, fallback_value)
