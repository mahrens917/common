from __future__ import annotations

"""Helper for validating market expiration dates"""


import logging
from datetime import date, datetime, timezone
from typing import Dict, Optional

logger = logging.getLogger("src.monitor.chart_generator")


class MarketExpirationValidator:
    """Validates whether markets expire on a given date"""

    def market_expires_today(
        self,
        market_data: Dict[str, str],
        today_et: date,
        et_timezone,
        market_key: str,
        today_market_date: str,
    ) -> bool:
        """
        Check if market resolves on today_et

        Args:
            market_data: Decoded market hash
            today_et: Today's date in ET
            et_timezone: ET timezone object
            market_key: Market key string
            today_market_date: Today's date in market format (e.g., "25JAN01")

        Returns:
            True if market expires today
        """

        def parse_iso(field: str, value: Optional[str]) -> Optional[datetime]:
            if value in (None, ""):
                return None
            try:
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError as exc:
                raise RuntimeError(f"Invalid timestamp for {field}: {value}") from exc
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(et_timezone)

        seen_metadata = False
        for field in ("expected_expiration_time", "expiration_time", "close_time"):
            dt = parse_iso(field, market_data.get(field))
            if dt is None:
                continue
            seen_metadata = True
            return dt.date() == today_et

        if not seen_metadata:
            raise RuntimeError(
                f"No expiration metadata available for {market_key}; cannot determine resolution date"
            )

        return today_market_date.lower() in market_key.lower()
