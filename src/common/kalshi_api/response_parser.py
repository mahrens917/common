"""Response parsing for Kalshi API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from common.data_models.trading import (
    OrderAction,
    OrderFill,
    OrderResponse,
    OrderSide,
    OrderStatus,
    OrderType,
)
from common.validation.required_fields import validate_required_fields as _validate_required_fields_common

from .client_helpers.errors import KalshiClientError
from .response_field_parser import ResponseFieldParser


class ResponseParser:
    """Parses Kalshi API responses into data models - slim coordinator."""

    @staticmethod
    def parse_order_fill(payload: Dict[str, Any]) -> OrderFill:
        """Parse an order fill from API response payload."""
        return ResponseFieldParser.parse_order_fill(payload)

    @staticmethod
    def normalise_fill(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize fill payload by parsing the timestamp field."""
        return ResponseFieldParser.normalise_fill(payload)

    @staticmethod
    def _parse_enum_fields(payload: Dict[str, Any], raw_values: Dict[str, Any]):
        """Parse enum fields from payload."""
        try:
            status = OrderStatus(str(raw_values["status_raw"]).lower())
            side = OrderSide(str(payload["side"]).lower())
            action = OrderAction(str(payload["action"]).lower())
            order_type = OrderType(str(payload["type"]).lower())
        except ValueError as exc:
            raise KalshiClientError("Unknown enum value in order payload") from exc
        return status, side, action, order_type

    @staticmethod
    def parse_order_response(
        payload: Dict[str, Any],
        trade_rule: Optional[str],
        trade_reason: Optional[str],
    ) -> OrderResponse:
        """Parse complete order response from API payload."""
        ResponseParser._validate_required_fields(payload)
        ResponseParser._validate_trade_metadata(trade_rule, trade_reason, payload)
        assert trade_rule is not None and trade_reason is not None

        raw_values = ResponseFieldParser.extract_raw_values(payload)
        timestamp = ResponseParser.parse_timestamp(raw_values["timestamp_raw"])
        average_fill_price = ResponseFieldParser.parse_average_fill_price(payload)
        fills = ResponseFieldParser.parse_fills_list(raw_values["fills_raw"])
        ticker = ResponseFieldParser.extract_ticker(payload)

        status, side, action, order_type = ResponseParser._parse_enum_fields(payload, raw_values)

        return OrderResponse(
            order_id=raw_values["order_id"],
            client_order_id=raw_values["client_order_id"],
            status=status,
            ticker=ticker,
            side=side,
            action=action,
            order_type=order_type,
            filled_count=raw_values["filled_count"],
            remaining_count=raw_values["remaining_count"],
            average_fill_price_cents=average_fill_price,
            timestamp=timestamp,
            fees_cents=raw_values["fees_cents"],
            fills=fills,
            trade_rule=trade_rule,
            trade_reason=trade_reason,
            rejection_reason=payload.get("rejection_reason"),
        )

    @staticmethod
    def _validate_required_fields(payload: Dict[str, Any]) -> None:
        required_fields = {
            "order_id",
            "client_order_id",
            "status",
            "filled_count",
            "remaining_count",
            "fees",
            "timestamp",
            "fills",
            "ticker",
            "side",
            "action",
            "type",
        }

        _validate_required_fields_common(payload, required_fields, error_cls=KalshiClientError)

    @staticmethod
    def _validate_trade_metadata(trade_rule: Optional[str], trade_reason: Optional[str], payload: Dict[str, Any]) -> None:
        order_id = payload.get("order_id")
        if order_id is None:
            raise KalshiClientError("Order payload missing order_id")
        if not trade_rule or not trade_reason:
            raise KalshiClientError(f"Order metadata missing trade rule/reason for order {order_id}")

    @staticmethod
    def parse_timestamp(timestamp_raw: Any) -> datetime | None:
        """Parse a timestamp string into a datetime object."""
        return ResponseFieldParser.parse_timestamp(timestamp_raw)
