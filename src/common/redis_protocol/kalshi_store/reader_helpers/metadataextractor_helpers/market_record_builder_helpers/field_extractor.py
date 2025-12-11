"""Extract and validate fields for market record building."""

import logging
from datetime import datetime
from typing import Any, Dict

import orjson

from common.redis_schema import build_kalshi_market_key

from ....market_skip import MarketSkip

logger = logging.getLogger(__name__)


def extract_and_merge_metadata(raw_hash: Dict[str, Any], market_ticker: str) -> Dict[str, Any]:
    """
    Extract metadata from raw hash and merge with snapshot.

    Args:
        raw_hash: Raw Redis hash
        market_ticker: Market ticker

    Returns:
        Combined metadata and snapshot dict
    """
    metadata_payload = raw_hash.get("metadata")
    metadata: Dict[str, Any] = {}
    if metadata_payload:
        try:
            metadata = orjson.loads(metadata_payload)
        except orjson.JSONDecodeError:
            logger.debug("Failed to decode metadata JSON for %s", market_ticker)

    combined: Dict[str, Any] = {}
    combined.update(metadata)
    combined.update(raw_hash)
    return combined


def validate_market_status(combined: Dict[str, Any], market_ticker: str, string_converter: Any) -> None:
    """
    Validate market status is not settled or closed.

    Args:
        combined: Combined metadata dict
        market_ticker: Market ticker
        string_converter: Function to convert to string

    Raises:
        MarketSkip: If market is settled or closed
    """
    status_value = string_converter(combined.get("status"))
    status_text = status_value.lower()
    if status_text in {"settled", "closed"}:
        raise MarketSkip("settled", f"Market {market_ticker} has status={status_text}")


def extract_and_validate_close_time(combined: Dict[str, Any], market_ticker: str, timestamp_normalizer: Any, now: datetime) -> str:
    """
    Extract and validate close time from market data.

    Args:
        combined: Combined metadata dict
        market_ticker: Market ticker
        timestamp_normalizer: Timestamp normalizer
        now: Current time

    Returns:
        Normalized close time string

    Raises:
        MarketSkip: If close time is missing or market is expired
    """
    close_time_value = combined.get("close_time") or combined.get("expected_expiration_time") or combined.get("expiration_time")
    if close_time_value in (None, "", b""):
        raise MarketSkip("missing_close_time", f"Market {market_ticker} missing close_time")

    normalized_close = timestamp_normalizer.normalize_timestamp(close_time_value) or str(close_time_value)
    try:
        close_dt = datetime.fromisoformat(normalized_close.replace("Z", "+00:00"))
    except ValueError:
        close_dt = None

    if close_dt and close_dt <= now:
        raise MarketSkip("expired", f"Market {market_ticker} expired at {normalized_close}")

    return normalized_close


def extract_and_validate_strike(combined: Dict[str, Any], market_ticker: str, strike_resolver: Any, string_converter: Any) -> float:
    """
    Extract and validate strike from market data.

    Args:
        combined: Combined metadata dict
        market_ticker: Market ticker
        strike_resolver: Strike resolver
        string_converter: Function to convert to string

    Returns:
        Strike value

    Raises:
        MarketSkip: If strike is missing
    """
    strike_value = strike_resolver.resolve_strike_from_combined(combined, string_converter)
    if strike_value is None:
        raise MarketSkip("missing_strike", f"Market {market_ticker} missing strike metadata")
    return strike_value


def build_record_dict(
    combined: Dict[str, Any],
    market_ticker: str,
    status_value: str,
    normalized_close: str,
    strike_value: float,
    currency: str,
    string_converter: Any,
) -> Dict[str, Any]:
    """
    Build market record dictionary from validated fields.

    Args:
        combined: Combined metadata dict
        market_ticker: Market ticker
        status_value: Market status
        normalized_close: Normalized close time
        strike_value: Strike value
        currency: Currency symbol
        string_converter: Function to convert to string

    Returns:
        Market record dict
    """
    strike_type_raw = combined.get("strike_type")
    strike_type_text = string_converter(strike_type_raw).lower()

    market_key = build_kalshi_market_key(market_ticker)
    return {
        "ticker": market_ticker,
        "market_ticker": market_ticker,
        "market_key": market_key,
        "status": status_value,
        "expiry": normalized_close,
        "close_time": normalized_close,
        "strike_type": string_converter(combined.get("strike_type"), strike_type_text) or strike_type_text,
        "strike": strike_value,
        "floor_strike": string_converter(combined.get("floor_strike")),
        "cap_strike": string_converter(combined.get("cap_strike")),
        "event_ticker": string_converter(combined.get("event_ticker")),
        "event_type": string_converter(combined.get("event_type")),
        "yes_bid": combined.get("yes_bid"),
        "yes_ask": combined.get("yes_ask"),
        "currency": currency.upper(),
    }
