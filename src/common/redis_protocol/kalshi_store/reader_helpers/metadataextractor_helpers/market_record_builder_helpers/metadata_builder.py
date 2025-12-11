"""Build combined metadata from Redis hash."""

import logging
from typing import Any, Dict

import orjson

from common.redis_schema import build_kalshi_market_key

logger = logging.getLogger(__name__)


class MetadataBuilder:
    """Builds combined metadata from Redis hash."""

    @staticmethod
    def build_combined(raw_hash: Dict[str, Any], type_converter) -> Dict[str, Any]:
        """Build combined metadata from snapshot and parsed JSON metadata."""
        snapshot = type_converter.normalize_hash(raw_hash)
        metadata = MetadataBuilder._parse_metadata_json(snapshot.get("metadata"))
        combined: Dict[str, Any] = {}
        combined.update(metadata)
        combined.update(snapshot)
        return combined

    @staticmethod
    def _parse_metadata_json(metadata_payload: Any) -> Dict[str, Any]:
        """Parse JSON metadata payload."""
        if not metadata_payload:
            return {}
        try:
            return orjson.loads(metadata_payload)
        except orjson.JSONDecodeError:
            logger.debug("Failed to decode metadata JSON")
            return {}

    @staticmethod
    def build_record(
        market_ticker: str,
        combined: Dict[str, Any],
        normalized_close: str,
        strike_value: Any,
        currency: str,
        type_converter,
    ) -> Dict[str, Any]:
        """Build final market record dictionary."""
        strike_type_raw = combined.get("strike_type")
        strike_type_text = type_converter.string_or_default(strike_type_raw).lower()
        market_key = build_kalshi_market_key(market_ticker)

        return {
            "ticker": market_ticker,
            "market_ticker": market_ticker,
            "market_key": market_key,
            "status": type_converter.string_or_default(combined.get("status")),
            "expiry": normalized_close,
            "close_time": normalized_close,
            "strike_type": type_converter.string_or_default(combined.get("strike_type"), strike_type_text) or strike_type_text,
            "strike": strike_value,
            "floor_strike": type_converter.string_or_default(combined.get("floor_strike")),
            "cap_strike": type_converter.string_or_default(combined.get("cap_strike")),
            "event_ticker": type_converter.string_or_default(combined.get("event_ticker")),
            "event_type": type_converter.string_or_default(combined.get("event_type")),
            "yes_bid": combined.get("yes_bid"),
            "yes_ask": combined.get("yes_ask"),
            "currency": currency.upper(),
        }
