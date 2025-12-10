"""Validation functions for trade record data."""

from typing import Any, Dict, Mapping

from common.exceptions import ValidationError
from common.validation.required_fields import (
    validate_required_fields as _validate_required_fields_common,
)

from ....data_models.trade_record import is_trade_reason_valid


def validate_required_fields(data: Dict[str, Any]) -> None:
    """Validate that all required fields are present in trade data."""
    required_fields = [
        "order_id",
        "market_ticker",
        "trade_timestamp",
        "trade_side",
        "quantity",
        "price_cents",
        "fee_cents",
        "cost_cents",
        "trade_rule",
        "trade_reason",
    ]

    def _error_factory(missing: list[str], _data: Mapping[str, Any]) -> ValidationError:
        first_missing = missing[0]
        return ValidationError(f"Missing required field '{first_missing}' in trade data")

    _validate_required_fields_common(
        data,
        required_fields,
        error_cls=ValidationError,
        on_missing=_error_factory,
    )


def validate_trade_metadata(data: Dict[str, Any]) -> None:
    """Validate trade metadata fields."""
    trade_rule = data["trade_rule"]
    trade_reason = data["trade_reason"]
    order_id = data["order_id"]

    if not trade_rule:
        raise ValueError(f"Empty trade_rule for order {order_id}")
    if not trade_reason:
        raise ValueError(f"Empty trade_reason for order {order_id}")
    if not is_trade_reason_valid(trade_reason):
        raise ValueError(f"Trade reason too short for order {order_id}: {trade_reason}")


def validate_weather_fields(data: Dict[str, Any]) -> None:
    """Validate weather-specific fields."""
    if "market_category" not in data:
        raise ValidationError("Missing required field 'market_category' in trade data")

    market_category = data["market_category"]
    weather_station = data.get("weather_station")
    if market_category == "weather" and not weather_station:
        raise ValidationError("Missing required field 'weather_station' in trade data")


def validate_trade_data(data: Dict[str, Any]) -> None:
    """Run all validation checks on trade data."""
    validate_required_fields(data)
    validate_trade_metadata(data)
    validate_weather_fields(data)
