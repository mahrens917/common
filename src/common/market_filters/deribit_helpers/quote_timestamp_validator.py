"""Quote timestamp validation utilities."""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional


class QuoteTimestampValidator:
    """Validates quote timestamp freshness."""

    @staticmethod
    def extract_timestamp(instrument: Any) -> Optional[datetime]:
        """
        Extract quote timestamp from instrument.

        Args:
            instrument: Instrument to extract from

        Returns:
            Quote timestamp or None
        """
        quote_timestamp = getattr(instrument, "quote_timestamp", None) or getattr(
            instrument, "mark_price_timestamp", None
        )

        if quote_timestamp is None:
            quote_timestamp = getattr(instrument, "timestamp", None)

        return quote_timestamp

    @staticmethod
    def validate_timestamp(
        quote_timestamp: Any,
        current_time: datetime,
        max_quote_age: timedelta,
    ) -> Optional[str]:
        """
        Validate quote timestamp.

        Args:
            quote_timestamp: Quote timestamp to validate
            current_time: Current time
            max_quote_age: Maximum allowed quote age

        Returns:
            Failure reason or None if valid
        """
        if not isinstance(quote_timestamp, datetime):
            return None

        # Normalize timezone
        normalized_ts = quote_timestamp
        if normalized_ts.tzinfo is None:
            normalized_ts = normalized_ts.replace(tzinfo=timezone.utc)

        # Check for future timestamps
        if normalized_ts > current_time + timedelta(seconds=5):
            return "future_quote"

        # Check for stale quotes
        if current_time - normalized_ts > max_quote_age:
            return "stale_quote"

        return None
