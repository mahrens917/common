"""Crypto market validation helpers."""

from __future__ import annotations

import re
from typing import Dict

_CRYPTO_MONTH_PATTERN = re.compile(r"\d{2}(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\d{2}")
_CRYPTO_ASSETS: tuple[str, ...] = ("BTC", "ETH")


def validate_crypto_ticker(ticker: str) -> bool:
    """Validate ticker contains crypto assets and month pattern."""
    if not ticker or not any(asset in ticker for asset in _CRYPTO_ASSETS):
        return False
    if not _CRYPTO_MONTH_PATTERN.search(ticker):
        return False
    return True


def validate_crypto_strikes(market: Dict[str, object]) -> bool:
    """Validate crypto market strike configuration."""
    cap_strike = market.get("cap_strike")
    floor_strike = market.get("floor_strike")

    if cap_strike is None and floor_strike is None:
        return False
    if cap_strike is not None and floor_strike is not None and cap_strike == floor_strike:
        return False
    return True
