from __future__ import annotations

"""Kalshi-related Redis key helpers for the unified schema."""


from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from .markets import KalshiMarketCategory, KalshiMarketKey

# Constants
_CONST_2 = 2
_CONST_4 = 4


@dataclass(frozen=True)
class KalshiMarketDescriptor:
    """Normalized representation of a Kalshi market ticker and its Redis key."""

    key: str
    category: KalshiMarketCategory
    ticker: str
    underlying: Optional[str]
    expiry_token: Optional[str]


def _classify_kalshi_ticker(
    display: str,
) -> Tuple[KalshiMarketCategory, Optional[str], Optional[str]]:
    """Infer category metadata from a normalized Kalshi ticker string."""

    category = KalshiMarketCategory.CUSTOM
    underlying: Optional[str] = None
    expiry_token: Optional[str] = None

    prefix_match = _match_supported_prefix(display)
    if prefix_match is None:
        _none_guard_value = category, underlying, expiry_token
        return _none_guard_value

    prefix, category = prefix_match
    parts = display.split("-")
    if len(parts) >= _CONST_2:
        if prefix == "KXHIGH":
            underlying = parts[0].replace(prefix, "") or None
            expiry_token = parts[1]
        else:
            underlying = parts[0]
            expiry_token = parts[1]

    return category, underlying, expiry_token


SUPPORTED_PREFIX_CATEGORIES: Dict[str, KalshiMarketCategory] = {
    "KXHIGH": KalshiMarketCategory.WEATHER,
    "KXBTC": KalshiMarketCategory.BINARY,
    "KXETH": KalshiMarketCategory.BINARY,
    "BTC-": KalshiMarketCategory.BINARY,
    "ETH-": KalshiMarketCategory.BINARY,
}


def _match_supported_prefix(display: str) -> Optional[Tuple[str, KalshiMarketCategory]]:
    for prefix, category in SUPPORTED_PREFIX_CATEGORIES.items():
        if display.startswith(prefix):
            return prefix, category
    return None


def describe_kalshi_ticker(ticker: str) -> KalshiMarketDescriptor:
    """Return normalized metadata for a Kalshi ticker string."""

    if not ticker or not ticker.strip():
        raise ValueError("Ticker must be a non-empty string")

    display = ticker.strip().upper()
    category, underlying, expiry_token = _classify_kalshi_ticker(display)
    key = KalshiMarketKey(category=category, ticker=display).key()

    return KalshiMarketDescriptor(
        key=key,
        category=category,
        ticker=display,
        underlying=underlying,
        expiry_token=expiry_token,
    )


def parse_kalshi_market_key(key: str) -> KalshiMarketDescriptor:
    """Convert a unified Kalshi Redis key into a structured descriptor."""

    if not key or not key.strip():
        raise TypeError("Key must be a non-empty string")

    parts = key.split(":")
    if len(parts) != _CONST_4:
        raise ValueError(f"Unexpected Kalshi key format: {key!r}")

    if parts[0] != "markets" or parts[1] != "kalshi":
        raise ValueError(f"Key is not within the Kalshi markets namespace: {key!r}")

    category_segment = parts[2]
    ticker_segment = parts[3]

    try:
        category = KalshiMarketCategory(category_segment)
    except ValueError as exc:
        raise ValueError(f"Unsupported Kalshi market category '{category_segment}' in {key!r}") from exc

    display = ticker_segment.upper()
    _, underlying, expiry_token = _classify_kalshi_ticker(display)

    descriptor = KalshiMarketDescriptor(
        key=key,
        category=category,
        ticker=display,
        underlying=underlying,
        expiry_token=expiry_token,
    )

    expected_key = KalshiMarketKey(category=descriptor.category, ticker=descriptor.ticker).key()
    if expected_key != key:
        raise ValueError(f"Kalshi key {key!r} does not match normalized form {expected_key!r}")

    return descriptor


def build_kalshi_market_key(ticker: str) -> str:
    """Return the unified Redis key for a Kalshi market ticker."""

    return describe_kalshi_ticker(ticker).key


def is_supported_kalshi_ticker(ticker: str) -> bool:
    """Return True when the ticker matches a supported Kalshi prefix."""

    if not ticker or not ticker.strip():
        return False
    display = ticker.strip().upper()
    return _match_supported_prefix(display) is not None
