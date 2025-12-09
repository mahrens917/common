"""Market expiry and close time checker."""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from ..time_utils import get_current_utc
from ..utils.dict_helpers import get_str

logger = logging.getLogger(__name__)


class ExpiryChecker:
    """Checks market expiry times and calculates time remaining."""

    def __init__(self, closure_warning_hours: float):
        """
        Initialize expiry checker.

        Args:
            closure_warning_hours: Hours before closure to trigger warnings
        """
        self.closure_warning_hours = closure_warning_hours

    def parse_close_time(self, market_data: Dict[str, Any]) -> Optional[datetime]:
        """
        Parse close time from market data.

        Args:
            market_data: Raw market data from API

        Returns:
            Close time as datetime or None if not available
        """
        ticker = market_data.get("ticker")
        if ticker is None:
            raise ValueError("Market data missing 'ticker' field")
        close_time_str = get_str(market_data, "close_time")

        if not close_time_str:
            return None

        try:
            return datetime.fromisoformat(close_time_str.replace("Z", "+00:00"))
        except (
            ValueError,
            AttributeError,
        ):
            logger.warning(
                "[ExpiryChecker] Invalid close_time value for %s: %s",
                ticker,
                close_time_str,
            )
            return None

    def calculate_time_to_close_hours(self, close_time: Optional[datetime]) -> float:
        """
        Calculate hours until market closes.

        Args:
            close_time: Market close time

        Returns:
            Hours until close (infinity if close_time is None)
        """
        if close_time is None:
            return float("inf")

        time_to_close = close_time - get_current_utc()
        return time_to_close.total_seconds() / 3600

    def is_closing_soon(self, time_to_close_hours: float) -> bool:
        """
        Check if market is closing soon.

        Args:
            time_to_close_hours: Hours until market closes

        Returns:
            True if within warning threshold
        """
        return 0 < time_to_close_hours <= self.closure_warning_hours
