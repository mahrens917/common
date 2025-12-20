"""Field parsing utilities for Kalshi API responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from common.data_models.trading import OrderFill
from common.time_utils import parse_timestamp

from .client_helpers.errors import KalshiClientError


class ResponseFieldParser:
    """Parse individual fields from Kalshi API responses."""

    @staticmethod
    def parse_timestamp(timestamp_raw: str) -> datetime | None:
        """Parse a timestamp string into a datetime object."""
        return parse_timestamp(timestamp_raw)

    @staticmethod
    def parse_order_fill(payload: Dict[str, Any]) -> OrderFill:
        """Parse an order fill from API response payload."""
        if "price" not in payload:
            raise KalshiClientError(f"Fill payload missing 'price': {payload}")
        price_source = payload["price"]
        count_raw = payload.get("count")
        if count_raw is None:
            raise KalshiClientError(f"Fill payload missing 'count': {payload}")
        if "timestamp" not in payload:
            raise KalshiClientError(f"Fill payload missing 'timestamp': {payload}")
        timestamp_raw = payload["timestamp"]
        try:
            price = int(price_source)
            count = int(count_raw)
        except (TypeError, ValueError) as exc:
            raise KalshiClientError(f"Invalid fill payload: {payload}") from exc
        timestamp = parse_timestamp(str(timestamp_raw))
        assert timestamp is not None
        return OrderFill(price_cents=price, count=count, timestamp=timestamp)

    @staticmethod
    def normalise_fill(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize fill payload by parsing the timestamp field."""
        normalised = dict(payload)
        if "timestamp" not in normalised:
            raise KalshiClientError(f"Fill payload missing timestamp: {payload}")
        try:
            parsed_timestamp = parse_timestamp(str(normalised["timestamp"]))
        except (ValueError, TypeError) as exc:
            raise KalshiClientError(f"Invalid fill timestamp: {payload}") from exc
        if parsed_timestamp is None:
            raise KalshiClientError(f"Invalid fill timestamp: {payload}")
        normalised["timestamp"] = parsed_timestamp
        return normalised

    @staticmethod
    def extract_raw_values(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract raw field values from order response payload."""
        try:
            order_id = str(payload["order_id"]).strip()
            client_order_id = str(payload["client_order_id"]).strip()
        except (TypeError, ValueError) as exc:
            raise KalshiClientError(f"Invalid order payload: {payload}") from exc
        if not order_id or not client_order_id:
            raise KalshiClientError(
                f"Order payload missing identifier data: order_id={payload['order_id']}, " f"client_order_id={payload['client_order_id']}"
            )
        try:
            return {
                "order_id": order_id,
                "client_order_id": client_order_id,
                "status_raw": payload["status"],
                "filled_count": int(payload["filled_count"]),
                "remaining_count": int(payload["remaining_count"]),
                "fees_cents": int(payload["fees"]),
                "timestamp_raw": payload["timestamp"],
                "fills_raw": payload["fills"],
            }
        except (TypeError, ValueError) as exc:
            raise KalshiClientError(f"Invalid order payload: {payload}") from exc

    @staticmethod
    def parse_average_fill_price(payload: Dict[str, Any]) -> Optional[int]:
        """Parse average fill price from order response payload."""
        average_price_raw = payload.get("average_fill_price")
        if average_price_raw is None:
            return None
        try:
            return int(average_price_raw)
        except (TypeError, ValueError) as exc:
            raise KalshiClientError(f"Invalid average fill price: {average_price_raw}") from exc

    @staticmethod
    def parse_fills_list(fills_raw: Any) -> List[OrderFill]:
        """Parse a list of order fills from API response."""
        if not isinstance(fills_raw, list):
            raise KalshiClientError("Order payload 'fills' must be a list")
        fills: List[OrderFill] = []
        if fills_raw:
            for fill_payload in fills_raw:
                if not isinstance(fill_payload, dict):
                    raise KalshiClientError("Order fill payload must be a JSON object")
                fills.append(ResponseFieldParser.parse_order_fill(fill_payload))
        return fills

    @staticmethod
    def extract_ticker(payload: Dict[str, Any]) -> str:
        """Extract and validate ticker from order response payload."""
        ticker = str(payload["ticker"]).strip()
        if not ticker:
            raise KalshiClientError(f"Order payload missing ticker: {payload}")
        return ticker
