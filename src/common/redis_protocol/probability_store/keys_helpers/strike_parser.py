"""Strike key parsing for probability store.

Delegates to canonical strike_helpers for parsing logic.
"""

from typing import Tuple

from ....strike_helpers import parse_strike_value
from ..exceptions import ProbabilityStoreError


class StrikeSortKeyParser:
    """Parses strike keys for deterministic sorting.

    Uses canonical strike_helpers for parsing, adds sort key tuple format.
    """

    @staticmethod
    def parse_plain_float(strike_key: str) -> Tuple[int, float]:
        """Parse plain numeric strike key."""
        value = parse_strike_value(strike_key)
        if value is None:
            raise ProbabilityStoreError(f"Invalid strike key '{strike_key}'")
        return (0, value)

    @staticmethod
    def parse_greater_than(strike_key: str) -> Tuple[int, float]:
        """Parse greater-than strike key (>value)."""
        value = parse_strike_value(strike_key[1:])
        if value is None:
            raise ProbabilityStoreError(f"Invalid strike key '{strike_key}'")
        return (1, value)

    @staticmethod
    def parse_less_than(strike_key: str) -> Tuple[int, float]:
        """Parse less-than strike key (<value)."""
        value = parse_strike_value(strike_key[1:])
        if value is None:
            raise ProbabilityStoreError(f"Invalid strike key '{strike_key}'")
        return (-1, value)

    @staticmethod
    def parse_range(strike_key: str) -> Tuple[int, float]:
        """Parse range strike key (start-end)."""
        start, _, _ = strike_key.partition("-")
        value = parse_strike_value(start)
        if value is None:
            raise ProbabilityStoreError(f"Invalid strike range '{strike_key}'")
        return (0, value)
