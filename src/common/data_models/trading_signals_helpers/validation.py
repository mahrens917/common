"""Validation logic for TradingSignal dataclass."""

from datetime import datetime
from typing import TYPE_CHECKING, cast

from src.common.exceptions import ValidationError

from ...constants import MAX_PRICE_CENTS, MIN_PRICE_CENTS

# Error messages
ERR_BUY_SELL_MISSING_FIELDS = "BUY/SELL signals must have action, side, and target_price_cents"
ERR_TARGET_PRICE_OUT_OF_RANGE = "Target price must be between {min}-{max} cents: {value}"
ERR_NO_TRADE_HAS_TRADE_FIELDS = "NO_TRADE signals must not have action, side, or target_price_cents"
ERR_TICKER_REQUIRED = "Ticker must be specified"
ERR_WEATHER_REASON_REQUIRED = "Weather reason must be specified"
ERR_TRADING_REASON_REQUIRED = "Trading reason must be specified"
ERR_TIMESTAMP_NOT_DATETIME_SIG = "Timestamp must be a datetime object"

if TYPE_CHECKING:
    from ..trading_signals import TradingSignal


def validate_trading_signal(signal: "TradingSignal") -> None:
    """Perform all validation checks on a trading signal."""
    from ..trading_signals import TradingSignalType

    if signal.signal_type in [TradingSignalType.BUY, TradingSignalType.SELL]:
        _validate_trade_signal_fields(signal)
    elif signal.signal_type == TradingSignalType.NO_TRADE:
        _validate_no_trade_signal(signal)

    _validate_required_fields(signal)


def _validate_trade_signal_fields(signal: "TradingSignal") -> None:
    """Validate BUY/SELL signal has required fields."""
    if signal.action is None or signal.side is None or signal.target_price_cents is None:
        raise ValueError(ERR_BUY_SELL_MISSING_FIELDS)

    target_price_cents = signal.target_price_cents
    if target_price_cents <= 0 or target_price_cents > MAX_PRICE_CENTS:
        raise ValidationError(
            ERR_TARGET_PRICE_OUT_OF_RANGE.format(
                min=MIN_PRICE_CENTS, max=MAX_PRICE_CENTS, value=signal.target_price_cents
            )
        )


def _validate_no_trade_signal(signal: "TradingSignal") -> None:
    """Validate NO_TRADE signal has no trade fields."""
    if any([signal.action, signal.side, signal.target_price_cents]):
        raise ValueError(ERR_NO_TRADE_HAS_TRADE_FIELDS)


def _validate_required_fields(signal: "TradingSignal") -> None:
    """Validate required fields are present."""
    if not signal.ticker:
        raise TypeError(ERR_TICKER_REQUIRED)

    if not signal.weather_reason:
        raise TypeError(ERR_WEATHER_REASON_REQUIRED)

    if not signal.trading_reason:
        raise TypeError(ERR_TRADING_REASON_REQUIRED)

    timestamp_value = cast(object, signal.timestamp)
    if not isinstance(timestamp_value, datetime):
        raise TypeError(ERR_TIMESTAMP_NOT_DATETIME_SIG)
