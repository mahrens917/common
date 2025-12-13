"""
Aggregator Utilities - Type coercion and conversion helpers

Utility functions for market aggregator operations.
"""

from typing import Any, Dict, List, Optional, Tuple

from common.redis_protocol.kalshi_store.utils_coercion import coerce_mapping as _coerce_mapping
from common.redis_protocol.kalshi_store.utils_coercion import string_or_default as _string_or_default
from common.redis_protocol.kalshi_store.utils_coercion import to_optional_float as canonical_to_optional_float


def coerce_mapping(candidate: Any) -> Dict[str, Any]:
    """Delegate mapping coercion to canonical helper."""
    return _coerce_mapping(candidate)


def to_optional_float(value: Any, *, context: str) -> Optional[float]:
    """Delegate optional float coercion to canonical helper."""
    return canonical_to_optional_float(value, context=context)


def string_or_default(value: Any, fallback_value: str = "") -> str:
    """Delegate string coercion to canonical helper."""
    return _string_or_default(value, fallback_value)


def build_strike_summary(
    grouped: Dict[Tuple[str, float, str], List[str]],
    market_by_ticker: Dict[str, Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    """Build strike summary for grouped markets."""
    summary: Dict[str, List[Dict[str, Any]]] = {}
    for (expiry, strike_value, strike_type), tickers in grouped.items():
        primary_ticker = tickers[0]
        base_market = coerce_mapping(market_by_ticker[primary_ticker])
        strike_info = {
            "strike": strike_value,
            "strike_type": strike_type,
            "floor_strike": to_optional_float(base_market.get("floor_strike"), context="floor_strike"),
            "cap_strike": to_optional_float(base_market.get("cap_strike"), context="cap_strike"),
            "market_tickers": tickers,
            "primary_market_ticker": primary_ticker,
            "event_type": string_or_default(base_market.get("event_type")),
            "event_ticker": string_or_default(base_market.get("event_ticker")),
            "t_yes_bid": None,
            "t_yes_ask": None,
            "interpolation_method": None,
            "deribit_points_used": None,
            "interpolation_quality_score": None,
        }
        bucket = summary.get(expiry)
        if bucket is None:
            bucket = []
            summary[expiry] = bucket
        bucket.append(strike_info)
    for expiry, strikes in summary.items():
        strikes.sort(key=lambda entry: float(entry["strike"]))
    return summary
