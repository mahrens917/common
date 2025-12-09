# ruff: noqa: PLR2004, PLR0913, PLR0911, PLR0912, PLR0915, C901
"""Validate and parse expiry token components."""

from typing import Optional, Tuple

# Constants extracted for ruff PLR2004 compliance
TOKEN_LEN_5 = 5


def validate_and_normalize_token(token: str) -> Optional[str]:
    """
    Validate token and return normalized version.

    Args:
        token: Raw token string

    Returns:
        Normalized token or None if invalid
    """
    if not token or len(token.strip()) < 5:
        return None
    return token.strip().upper()


def parse_token_components(token: str) -> Tuple[int, str, str]:
    """
    Parse token into components.

    Args:
        token: Normalized token string

    Returns:
        Tuple of (month, prefix, remainder)

    Raises:
        ValueError: If token format is invalid
    """
    month = _parse_month_code(token)
    prefix = token[:2]
    remainder = token[5:]

    if not prefix.isdigit():
        raise TypeError(f"Invalid prefix in token '{token}': must be digits")

    return month, prefix, remainder


def _parse_month_code(token: str) -> int:
    """Parse month code from token."""
    month_map = {
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
    month_code = token[2:5]
    month = month_map.get(month_code)
    if month is None:
        raise ValueError(f"Unknown month code in expiry token '{token}'")
    return month
