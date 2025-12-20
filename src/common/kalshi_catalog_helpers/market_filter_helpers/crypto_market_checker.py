"""Crypto market identification logic."""

from typing import Dict, Tuple

from .crypto_pattern_matcher import value_matches_crypto

_CRYPTO_FIELD_CANDIDATES: Tuple[str, ...] = (
    "currency",
    "underlying",
    "underlying_symbol",
    "underlying_asset",
    "asset",
    "series_ticker",
    "product_ticker",
)


def is_crypto_market(market: Dict[str, object]) -> bool:
    """Check if market is crypto-related."""
    ticker = market.get("ticker")
    if isinstance(ticker, str) and value_matches_crypto(ticker):
        return True

    for field in _CRYPTO_FIELD_CANDIDATES:
        value = market.get(field)
        if isinstance(value, str) and value_matches_crypto(value):
            return True

    return False
