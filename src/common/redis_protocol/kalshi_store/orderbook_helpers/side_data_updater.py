"""Side data update logic for orderbook deltas."""

from __future__ import annotations

import logging
from typing import Dict

import orjson

logger = logging.getLogger(__name__)


class SideDataUpdater:
    """Updates orderbook side data (bids/asks) based on deltas."""

    @staticmethod
    def parse_side_data(side_json: bytes | str | None) -> Dict:
        """Parse side data JSON from Redis.

        Returns empty dict for genuinely empty fields (None/empty bytes).
        Logs at error level and returns empty dict on corrupted JSON so
        data integrity issues are visible to monitoring without crashing
        the processing pipeline.
        """
        if side_json is None or side_json in {b"", ""}:
            return {}

        try:
            side_data = orjson.loads(side_json)
        except (orjson.JSONDecodeError, TypeError) as exc:  # Expected: corrupted Redis data  # policy_guard: allow-silent-handler
            logger.error("Corrupted orderbook side data in Redis: %s", exc, exc_info=True)
            return {}

        if not isinstance(side_data, dict):
            logger.error("Orderbook side data is not a dict: %s", type(side_data).__name__)
            return {}

        return side_data

    @staticmethod
    def apply_delta(side_data: Dict, price_str: str, delta: float) -> Dict:
        """Apply delta to side data and return updated dict.

        Args:
            side_data: Current side data dictionary
            price_str: Price level as string
            delta: Size delta to apply

        Returns:
            Updated side data dictionary
        """
        if price_str in side_data:
            current_size = side_data[price_str]
        else:
            current_size = 0

        new_size = current_size + delta
        if new_size <= 0:
            side_data.pop(price_str, None)
        else:
            side_data[price_str] = new_size

        return side_data
