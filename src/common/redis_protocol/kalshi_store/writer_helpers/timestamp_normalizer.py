"""
Timestamp normalization utilities.

This module handles conversion and normalization of various timestamp formats.
Delegates to canonical implementation in utils_market.py.
"""

from typing import Any

from ..utils_market import normalise_trade_timestamp


class TimestampNormalizer:
    """
    Handles timestamp normalization for trade data.

    Delegates to canonical implementation in kalshi_store.utils_market.
    """

    @staticmethod
    def normalise_trade_timestamp(value: Any) -> str:
        """
        Convert Kalshi trade timestamps to ISO8601.

        Delegates to canonical implementation in kalshi_store.utils_market.
        """
        return normalise_trade_timestamp(value)
