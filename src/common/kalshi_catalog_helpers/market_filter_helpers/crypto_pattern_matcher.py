"""Crypto pattern matching logic."""

import re
from typing import Tuple

_TOKEN_SPLIT_PATTERN = re.compile(r"[^A-Z0-9]+")
_CRYPTO_TICKER_PREFIXES: Tuple[str, ...] = ("BTC", "ETH", "KXBTC", "KXETH")
_CRYPTO_ASSETS: Tuple[str, ...] = ("BTC", "ETH")


def matches_crypto_prefix(value_upper: str) -> bool:
    """Check if value starts with known crypto prefixes."""
    return any(value_upper.startswith(prefix) for prefix in _CRYPTO_TICKER_PREFIXES)


def token_matches_crypto(token: str) -> bool:
    """Check if single token matches crypto patterns."""
    if any(token.startswith(prefix) for prefix in _CRYPTO_TICKER_PREFIXES):
        return True

    for asset in _CRYPTO_ASSETS:
        if token_matches_asset(token, asset):
            return True
    return False


def token_matches_asset(token: str, asset: str) -> bool:
    """Check if token matches specific crypto asset."""
    if token == asset:
        return True

    if token.startswith(asset):
        remainder = token[len(asset) :]
        if not remainder or remainder[0].isdigit():
            return True
        if remainder.startswith(("MAX", "MIN", "T", "B", "USD")):
            return True
    return False


def value_matches_crypto(value: str) -> bool:
    """Check if value matches crypto patterns."""
    value_upper = value.upper()
    if matches_crypto_prefix(value_upper):
        return True

    tokens = [token for token in _TOKEN_SPLIT_PATTERN.split(value_upper) if token]
    return any(token_matches_crypto(token) for token in tokens)
