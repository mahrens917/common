"""Validation logic for TradeRecord dataclass."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from src.common.exceptions import ValidationError

from ...redis_schema.markets import KalshiMarketCategory
from .trade_record_utils import is_trade_reason_valid

# Error messages
ERR_MISSING_REQUIRED_FIELD = "Trade record missing required field: {field}"
ERR_INVALID_TRADE_AMOUNT = "Trade amount must be positive: {value}"

if TYPE_CHECKING:
    from ..trade_record import TradeRecord


# Constants
_CONST_100 = 100
_MAX_PRICE = 99


def validate_basic_fields(trade: "TradeRecord") -> None:
    """Validate basic required fields."""

    if not trade.order_id:
        raise ValueError("Order ID must be specified")

    if not trade.market_ticker:
        raise ValueError("Market ticker must be specified")

    timestamp = getattr(trade, "trade_timestamp", None)
    if not isinstance(timestamp, datetime):
        raise TypeError(f"Trade timestamp must be datetime, got: {type(timestamp)}")


def validate_trade_side(trade_side: Any) -> None:
    """Validate trade side is correct enum type."""
    from ..trade_record import TradeSide

    if not isinstance(trade_side, TradeSide):
        raise TypeError(f"Trade side must be TradeSide enum, got: {type(trade_side)}")


def validate_quantity_and_price(quantity: int, price_cents: int, fee_cents: int) -> None:
    """Validate quantity, price, and fee values."""

    if quantity <= 0:
        raise ValueError(f"Quantity must be positive: {quantity}")

    if price_cents <= 0 or price_cents > _MAX_PRICE:
        raise ValueError(f"Price must be between 1-99 cents: {price_cents}")

    if fee_cents < 0:
        raise ValueError(f"Fee cannot be negative: {fee_cents}")


def validate_cost_calculation(
    price_cents: int, quantity: int, fee_cents: int, cost_cents: int
) -> None:
    """Validate cost calculation: cost = (price * quantity) + fees."""

    expected_cost = (price_cents * quantity) + fee_cents

    if cost_cents != expected_cost:
        raise ValueError(f"Cost mismatch: expected {expected_cost}, got {cost_cents}")


def validate_and_normalize_category(market_category: str) -> str:
    """Validate market category and return normalized value."""

    if not market_category:
        raise ValueError("Market category must be specified")

    try:
        category_value = (
            market_category.value
            if isinstance(market_category, KalshiMarketCategory)
            else KalshiMarketCategory(market_category.lower()).value
        )
    except ValueError as exc:
        raise ValueError(f"Unsupported market category: {market_category}") from exc

    return category_value


def validate_weather_station(weather_station: str | None, market_category: str) -> str | None:
    """Validate weather station for weather category trades."""

    if market_category == KalshiMarketCategory.WEATHER.value:
        if not weather_station:
            raise ValueError("Weather station must be specified for weather trades")
        normalized = weather_station.upper()
        if len(normalized) not in {2, 3, 4}:
            raise ValidationError(
                f"Weather station must be a 2-4 letter station code, got: {weather_station}"
            )
        return normalized

    return weather_station


def validate_trade_metadata(trade_rule: str, trade_reason: str) -> None:
    """Validate trade rule and reason fields."""

    if not trade_rule:
        raise ValueError("Trade rule must be specified")

    if not trade_reason:
        raise ValueError("Trade reason must be specified")

    if not is_trade_reason_valid(trade_reason):
        raise ValueError("Trade reason must be descriptive (min 10 characters)")


def validate_settlement_data(
    settlement_price_cents: int | None, settlement_time: Any | None
) -> None:
    """Validate settlement price and time if present."""

    if settlement_price_cents is not None:
        if not 0 <= settlement_price_cents <= _CONST_100:
            raise ValueError(
                f"Settlement price must be between 0 and 100 cents: {settlement_price_cents}"
            )

    if settlement_time is not None and not isinstance(settlement_time, datetime):
        raise ValueError("Settlement time must be a datetime instance")


def validate_trade_record(trade: "TradeRecord") -> None:
    """Perform all validation checks on a trade record."""

    validate_basic_fields(trade)
    validate_trade_side(trade.trade_side)
    validate_quantity_and_price(trade.quantity, trade.price_cents, trade.fee_cents)
    validate_cost_calculation(trade.price_cents, trade.quantity, trade.fee_cents, trade.cost_cents)

    # Normalize and validate category
    trade.market_category = validate_and_normalize_category(trade.market_category)

    # Validate and normalize weather station
    trade.weather_station = validate_weather_station(trade.weather_station, trade.market_category)

    validate_trade_metadata(trade.trade_rule, trade.trade_reason)
    validate_settlement_data(trade.settlement_price_cents, trade.settlement_time)
