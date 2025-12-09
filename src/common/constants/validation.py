"""Validation constants.

These constants define validation thresholds and constraints used throughout
the codebase for data integrity checks.
"""

# Key parsing constants
MIN_KEY_PARTS = 5  # Minimum number of parts in a Kalshi key

# String validation constants
MIN_TRADE_REASON_LENGTH = 10  # Minimum length for trade reason strings

# Resource utilization thresholds
UTILIZATION_WARNING_THRESHOLD = 80  # Percentage threshold for resource warnings

__all__ = [
    "MIN_KEY_PARTS",
    "MIN_TRADE_REASON_LENGTH",
    "UTILIZATION_WARNING_THRESHOLD",
]
