"""Validate market close times."""

import datetime
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class CloseTimeValidator:
    """Validates market close times."""

    @staticmethod
    def is_in_future(market: Dict[str, object], now_ts: float) -> bool:
        """Check if market close time is in the future."""
        close_candidates = (
            "close_time",
            "expected_expiration_time",
            "expiration_time",
            "latest_expiration_time",
            "close_time_ts",
        )

        for field in close_candidates:
            close_value = market.get(field)
            if close_value in (None, ""):
                continue
            parsed = CloseTimeValidator._parse_close_time(close_value)
            if parsed is None:
                logger.debug(
                    "Could not parse %s '%s' for market %s",
                    field,
                    close_value,
                    market.get("ticker"),
                )
                continue
            return parsed > now_ts

        logger.debug("Market %s missing all close/expiration timestamps", market.get("ticker"))
        return False

    @staticmethod
    def _parse_close_time(close_time: object) -> Optional[float]:
        """Parse close time to timestamp.

        Returns:
            Timestamp as float, or None if input type is not supported.

        Raises:
            ValueError: When string cannot be parsed as ISO format.
        """
        if isinstance(close_time, (int, float)):
            return float(close_time)

        if isinstance(close_time, str):
            try:
                return datetime.datetime.fromisoformat(
                    close_time.replace("Z", "+00:00")
                ).timestamp()
            except ValueError:
                return None

        return None
