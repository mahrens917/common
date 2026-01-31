"""
Price history data parsing utilities

Handles parsing of sorted set entries from Redis ZRANGEBYSCORE results.
"""

from __future__ import annotations

import logging
from typing import Tuple

from common.price_history_utils import parse_history_member_value

logger = logging.getLogger(__name__)


class PriceHistoryParser:
    """
    Parses price history sorted set entries

    Extracts price values from sorted set members and validates data.
    """

    @staticmethod
    def parse_sorted_set_entry(member: str | bytes, score: float) -> Tuple[int, float] | None:
        """
        Parse a sorted set entry into (timestamp, price).

        Args:
            member: Sorted set member in 'ts|price' format
            score: The score (unix timestamp) from ZRANGEBYSCORE

        Returns:
            Tuple of (timestamp, price) if valid, None otherwise
        """
        try:
            price = parse_history_member_value(member)
            if price > 0:
                return (int(score), price)
        except (  # policy_guard: allow-silent-handler
            ValueError,
            TypeError,
        ):
            logger.warning("Skipping invalid sorted set entry: %s", member)

        return None
