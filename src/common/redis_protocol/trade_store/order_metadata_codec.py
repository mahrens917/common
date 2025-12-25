"""Order metadata serialisation and validation."""

from datetime import datetime
from typing import Any, Callable, Dict, Optional

import orjson

from ...data_models.trade_record import is_trade_reason_valid
from .errors import OrderMetadataError

JsonLike = str | bytes | Dict[str, Any]


class OrderMetadataCodec:
    """Handle order metadata serialisation and validation."""

    def __init__(self, timestamp_provider: Callable[[], datetime]) -> None:
        self._timestamp_provider = timestamp_provider

    def encode(
        self,
        *,
        order_id: str,
        trade_rule: str,
        trade_reason: str,
        market_category: Optional[str],
        weather_station: Optional[str],
    ) -> str:
        """Encode order metadata to JSON."""
        if not trade_rule:
            raise OrderMetadataError(f"Empty trade_rule for order {order_id}")
        if not trade_reason:
            raise OrderMetadataError(f"Empty trade_reason for order {order_id}")
        if not is_trade_reason_valid(trade_reason):
            raise OrderMetadataError(f"Trade reason too short for order {order_id}: {trade_reason}")
        if market_category is not None and not market_category:
            raise OrderMetadataError(f"Empty market_category for order {order_id}")

        metadata: Dict[str, Any] = {
            "trade_rule": trade_rule,
            "trade_reason": trade_reason,
            "stored_timestamp": self._timestamp_provider().isoformat(),
        }
        if market_category is not None:
            metadata["market_category"] = market_category
        if weather_station is not None:
            metadata["weather_station"] = weather_station
        return orjson.dumps(metadata).decode("utf-8")

    def decode(self, payload: JsonLike, *, order_id: str) -> Dict[str, str]:
        """Decode order metadata from JSON."""
        metadata = self._parse_payload(payload, order_id)
        self._validate_required_fields(metadata, order_id)
        self._validate_trade_reason(metadata, order_id)
        self._validate_market_category(metadata, order_id)
        return self._build_result(metadata)

    def _parse_payload(self, payload: JsonLike, order_id: str) -> Dict[str, Any]:
        """Parse payload to dict."""
        match payload:
            case dict():
                return payload
            case bytes():
                text_payload = payload.decode("utf-8")
            case str():
                text_payload = payload
            case _:
                raise TypeError(f"Unsupported metadata payload for {order_id}: {type(payload)!r}")

        try:
            return orjson.loads(text_payload)
        except orjson.JSONDecodeError as exc:
            raise OrderMetadataError(f"Stored metadata for {order_id} is not valid JSON") from exc

    @staticmethod
    def _validate_required_fields(metadata: Dict[str, Any], order_id: str) -> None:
        """Validate required fields present."""
        required = {"trade_rule", "trade_reason"}
        missing = required - metadata.keys()
        if missing:
            raise OrderMetadataError(f"Stored metadata for {order_id} is missing required fields: {missing}")

    @staticmethod
    def _validate_trade_reason(metadata: Dict[str, Any], order_id: str) -> None:
        """Validate trade reason."""
        trade_reason = metadata["trade_reason"]
        if not is_trade_reason_valid(trade_reason):
            raise OrderMetadataError(f"Stored trade reason too short for order {order_id}: {trade_reason}")

    @staticmethod
    def _validate_market_category(metadata: Dict[str, Any], order_id: str) -> None:
        """Validate market category present."""
        if "market_category" not in metadata:
            raise OrderMetadataError(f"Stored metadata for {order_id} is missing required field 'market_category'")

    @staticmethod
    def _build_result(metadata: Dict[str, Any]) -> Dict[str, str]:
        """Build result dict."""
        result = {
            "trade_rule": metadata["trade_rule"],
            "trade_reason": metadata["trade_reason"],
            "market_category": metadata["market_category"],
        }
        if "weather_station" in metadata and metadata["weather_station"]:
            result["weather_station"] = metadata["weather_station"]
        return result
