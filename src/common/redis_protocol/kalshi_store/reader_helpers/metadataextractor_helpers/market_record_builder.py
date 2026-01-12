"""
Market Record Builder - Build market records from Redis data

Constructs complete market records with validation and skip logic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

import orjson

from common.redis_schema import build_kalshi_market_key
from common.truthy import pick_if

from ...market_skip import MarketSkip

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MarketRecordData:
    """Data required to build a market record."""

    market_ticker: str
    market_key: str
    status_value: str
    normalized_close: str
    strike_type_text: str
    strike_value: float
    combined: Dict[str, Any]
    type_converter: Any
    currency: Optional[str]


class MarketRecordBuilder:
    """Build market records from raw Redis hashes"""

    def __init__(
        self,
        type_converter: Any,
        timestamp_normalizer: Any,
        strike_resolver: Any,
    ):
        self.type_converter = type_converter
        self.timestamp_normalizer = timestamp_normalizer
        self.strike_resolver = strike_resolver

    def create_market_record(
        self,
        market_ticker: str,
        raw_hash: Dict[str, Any],
        *,
        currency: Optional[str],
        now: datetime,
    ) -> Dict[str, Any]:
        if not raw_hash:
            raise MarketSkip("missing_metadata", f"No Redis hash for {market_ticker}")

        snapshot = self.type_converter.normalize_hash(raw_hash)
        metadata = _decode_metadata_payload(snapshot.get("metadata"), market_ticker)
        combined = _merge_snapshot_with_metadata(metadata, snapshot)

        status_value = self.type_converter.string_or_default(combined.get("status"))
        _ensure_market_open(status_value, market_ticker)

        close_time_value = _extract_close_time(combined, market_ticker)
        normalized_close, close_dt = _normalize_close_time(close_time_value, self.timestamp_normalizer)
        _ensure_not_expired(close_dt, normalized_close, market_ticker, now)

        strike_value = _resolve_strike_value(
            self.strike_resolver,
            combined,
            self.type_converter.string_or_default,
            market_ticker,
        )

        strike_type_text = self.type_converter.string_or_default(combined.get("strike_type")).lower()
        market_key = build_kalshi_market_key(market_ticker)
        data = MarketRecordData(
            market_ticker=market_ticker,
            market_key=market_key,
            status_value=status_value,
            normalized_close=normalized_close,
            strike_type_text=strike_type_text,
            strike_value=strike_value,
            combined=combined,
            type_converter=self.type_converter,
            currency=currency,
        )
        return _build_market_record(data)


def _decode_metadata_payload(payload: Any, market_ticker: str) -> Dict[str, Any]:
    """Decode metadata JSON payload if present."""
    if not payload:
        return {}
    try:
        decoded = orjson.loads(payload)
        return pick_if(isinstance(decoded, dict), lambda: decoded, lambda: {})
    except orjson.JSONDecodeError:  # Expected exception in operation  # policy_guard: allow-silent-handler
        logger.debug("Failed to decode metadata JSON for %s", market_ticker)
        return {}


def _merge_snapshot_with_metadata(metadata: Dict[str, Any], snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Combine metadata JSON with normalized snapshot fields."""
    combined: Dict[str, Any] = {}
    combined.update(metadata)
    combined.update(snapshot)
    return combined


def _ensure_market_open(status_value: str, market_ticker: str) -> None:
    """Raise when the market is already closed/settled."""
    status_text = status_value.lower()
    if status_text in {"settled", "closed"}:
        raise MarketSkip("settled", f"Market {market_ticker} has status={status_text}")


def _extract_close_time(combined: Dict[str, Any], market_ticker: str) -> Any:
    """Get the first available close time representation."""
    close_time_value = combined.get("close_time") or combined.get("expected_expiration_time") or combined.get("expiration_time")
    if close_time_value in (None, "", b""):
        raise MarketSkip("missing_close_time", f"Market {market_ticker} missing close_time")
    return close_time_value


def _normalize_close_time(close_time: Any, timestamp_normalizer: Any) -> tuple[str, Optional[datetime]]:
    """Normalize close time and convert to datetime when possible."""
    normalized_close = timestamp_normalizer.normalize_timestamp(close_time) or str(close_time)
    try:
        close_dt = datetime.fromisoformat(normalized_close.replace("Z", "+00:00"))
    except ValueError:  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
        close_dt = None
    return normalized_close, close_dt


def _ensure_not_expired(
    close_dt: Optional[datetime],
    normalized_close: str,
    market_ticker: str,
    now: datetime,
) -> None:
    """Ensure the market has not already expired."""
    if close_dt and close_dt <= now:
        raise MarketSkip("expired", f"Market {market_ticker} expired at {normalized_close}")


def _resolve_strike_value(
    strike_resolver: Any,
    combined: Dict[str, Any],
    string_or_default: Any,
    market_ticker: str,
) -> float:
    """Resolve the strike value or raise skip error."""
    strike_value = strike_resolver.resolve_strike_from_combined(combined, string_or_default)
    if strike_value is None:
        raise MarketSkip("missing_strike", f"Market {market_ticker} missing strike metadata")
    return strike_value


def _build_market_record(data: MarketRecordData) -> Dict[str, Any]:
    """Assemble the final market record dict."""
    strike_type = data.type_converter.string_or_default(data.combined.get("strike_type"), data.strike_type_text) or data.strike_type_text
    currency_value = data.currency.upper() if data.currency else None
    result = {
        "ticker": data.market_ticker,
        "market_ticker": data.market_ticker,
        "market_key": data.market_key,
        "status": data.status_value,
        "expiry": data.normalized_close,
        "close_time": data.normalized_close,
        "strike_type": strike_type,
        "strike": data.strike_value,
        "floor_strike": data.type_converter.string_or_default(data.combined.get("floor_strike")),
        "cap_strike": data.type_converter.string_or_default(data.combined.get("cap_strike")),
        "event_ticker": data.type_converter.string_or_default(data.combined.get("event_ticker")),
        "event_type": data.type_converter.string_or_default(data.combined.get("event_type")),
        "category": data.type_converter.string_or_default(data.combined.get("category")),
        "yes_bid": data.combined.get("yes_bid"),
        "yes_ask": data.combined.get("yes_ask"),
        "currency": currency_value,
        "yes_bid_size": data.combined.get("yes_bid_size"),
        "yes_ask_size": data.combined.get("yes_ask_size"),
        "yes_bids": data.combined.get("yes_bids"),
        "yes_asks": data.combined.get("yes_asks"),
    }
    return result
