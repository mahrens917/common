"""Metadata extraction utilities — parsing, syncing, and price extraction."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import orjson

from ...utils_coercion import sync_top_of_book_fields as canonical_sync_top_of_book

logger = logging.getLogger(__name__)


# --- Metadata parsing ---


def parse_market_metadata(market_ticker: str, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Parse metadata JSON from market data hash.

    Args:
        market_ticker: Ticker for logging
        market_data: Market data hash

    Returns:
        Parsed metadata dict or None if invalid
    """
    metadata_blob = market_data.get("metadata") if market_data else None
    if metadata_blob is None:
        return None
    try:
        return orjson.loads(metadata_blob)
    except orjson.JSONDecodeError:  # Expected exception, returning default value  # policy_guard: allow-silent-handler
        logger.warning("Invalid metadata JSON for market %s", market_ticker)
        return None


# --- Orderbook syncing ---


def sync_top_of_book_fields(snapshot: Dict[str, Any]) -> None:
    """Delegate to canonical top-of-book sync to keep logic consistent."""
    _sync_top_of_book_fields(snapshot)


def _sync_top_of_book_fields(snapshot: Dict[str, Any]) -> None:
    """Module-level helper retained for test patching."""
    canonical_sync_top_of_book(snapshot)


# --- Price extraction ---


def extract_market_prices(metadata: Dict[str, Any]) -> tuple[Optional[float], Optional[float]]:
    """Extract best bid and ask prices from metadata.

    Args:
        metadata: Market metadata dict

    Returns:
        Tuple of (best_bid, best_ask) or None values
    """

    def _coerce(value: Any) -> Optional[float]:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (  # policy_guard: allow-silent-handler
            TypeError,
            ValueError,
        ):
            return None

    return _coerce(metadata.get("yes_bid")), _coerce(metadata.get("yes_ask"))
