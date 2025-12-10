"""
Expiry date conversion utilities for OptimizedMarketStore
"""

import logging
import re
from datetime import datetime, timezone

from common.exceptions import DataError

from ...time_utils import DERIBIT_EXPIRY_HOUR, EPOCH_START, validate_expiry_hour

logger = logging.getLogger(__name__)


class ExpiryConverter:
    """Handles conversion between different expiry date formats"""

    @staticmethod
    def convert_iso_to_deribit(expiry: str) -> str:
        try:
            expiry_dt = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
            months = [
                "JAN",
                "FEB",
                "MAR",
                "APR",
                "MAY",
                "JUN",
                "JUL",
                "AUG",
                "SEP",
                "OCT",
                "NOV",
                "DEC",
            ]
            month_str = months[expiry_dt.month - 1]
            day_str = str(expiry_dt.day)
            return f"{day_str}{month_str}{expiry_dt.year % 100:02d}"
        except (ValueError, IndexError) as exc:
            logger.exception("Error converting ISO to Deribit format: %s, error: %s")
            raise DataError(
                f"Failed to convert ISO to Deribit format for '{expiry}': {exc}"
            ) from exc

    @staticmethod
    def convert_expiry_to_iso(expiry: str) -> str:
        try:
            match = re.match(r"(\d{1,2})([A-Z]{3})(\d{2})", expiry)
            if not match:
                return expiry

            day = int(match.group(1))
            month_str = match.group(2)
            year = 2000 + int(match.group(3))
            months = {
                "JAN": 1,
                "FEB": 2,
                "MAR": 3,
                "APR": 4,
                "MAY": 5,
                "JUN": 6,
                "JUL": 7,
                "AUG": 8,
                "SEP": 9,
                "OCT": 10,
                "NOV": 11,
                "DEC": 12,
            }
            month = months[month_str]
            expiry_date = datetime(year, month, day, DERIBIT_EXPIRY_HOUR, 0, 0, tzinfo=timezone.utc)
            if expiry_date < EPOCH_START or not validate_expiry_hour(
                expiry_date, DERIBIT_EXPIRY_HOUR
            ):
                return expiry
            return expiry_date.isoformat()
        except (ValueError, KeyError) as exc:
            logger.exception("Error converting Deribit to ISO format: %s, error: %s")
            raise DataError(
                f"Failed to convert Deribit to ISO format for '{expiry}': {exc}"
            ) from exc
