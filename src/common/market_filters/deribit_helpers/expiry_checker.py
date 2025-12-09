"""Expiry checking utilities."""

from datetime import datetime, timezone
from typing import Any, Optional


class ExpiryChecker:
    """Checks instrument expiry status."""

    @staticmethod
    def normalize_expiry(value: Any) -> Optional[datetime]:
        """
        Normalize expiry to UTC timezone.

        Args:
            value: Expiry value to normalize

        Returns:
            Normalized datetime or None
        """
        if value is None:
            return None

        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)

        return None

    @staticmethod
    def is_expired(expiry: Optional[datetime], current_time: datetime) -> bool:
        """
        Check if instrument is expired.

        Args:
            expiry: Expiry datetime
            current_time: Current time

        Returns:
            True if expired
        """
        return expiry is not None and expiry <= current_time
