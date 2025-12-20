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
        """Parse side data JSON, returning empty dict on error."""
        if not side_json:
            return {}

        try:
            side_data = orjson.loads(side_json)
        except (orjson.JSONDecodeError, TypeError) as exc:  # policy_guard: allow-silent-handler
            logger.warning("Error parsing side data: %s, initializing empty", exc)
            return {}

        if not isinstance(side_data, dict):
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
