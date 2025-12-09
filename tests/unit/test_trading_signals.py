from datetime import datetime, timezone

import pytest

from src.common.data_models.trading import OrderAction, OrderSide
from src.common.data_models.trading_signals import (
    TradingSignal,
    TradingSignalBatch,
    TradingSignalType,
)

_CONST_45 = 45


def _base_signal_kwargs():
    """Factory returning baseline valid TradingSignal keyword arguments."""

    return {
        "signal_type": TradingSignalType.BUY,
        "action": OrderAction.BUY,
        "side": OrderSide.YES,
        "target_price_cents": 45,
        "ticker": "WX-TICKER-001",
        "confidence": "HIGH",
        "timestamp": datetime(2025, 1, 1, tzinfo=timezone.utc),
        "weather_reason": "Warm front arriving with sustained temps above threshold.",
        "trading_reason": "Spread mispriced relative to updated forecast and liquidity.",
        "current_temperature_f": 38.5,
        "strike_threshold": 35.0,
        "expected_profit_cents": 12,
    }


def test_trading_signal_accepts_valid_buy_signal():
    signal = TradingSignal(**_base_signal_kwargs())
    assert signal.signal_type == TradingSignalType.BUY
    assert signal.target_price_cents == _CONST_45


@pytest.mark.parametrize("target_price", [0, 100])
def test_trading_signal_enforces_price_bounds(target_price):
    kwargs = _base_signal_kwargs()
    kwargs["target_price_cents"] = target_price
    with pytest.raises(ValueError, match="Target price must be between 1-99"):
        TradingSignal(**kwargs)


def test_trading_signal_requires_core_fields_for_buy_signals():
    kwargs = _base_signal_kwargs()
    kwargs["action"] = None
    with pytest.raises(ValueError, match="must have action, side, and target_price_cents"):
        TradingSignal(**kwargs)


def test_trading_signal_no_trade_disallows_trade_fields():
    kwargs = _base_signal_kwargs()
    kwargs["signal_type"] = TradingSignalType.NO_TRADE
    with pytest.raises(ValueError, match="must not have action, side, or target_price_cents"):
        TradingSignal(**kwargs)


@pytest.mark.parametrize(
    "field_name, bad_value, error_message",
    [
        ("ticker", "", "Ticker must be specified"),
        ("weather_reason", "", "Weather reason must be specified"),
        ("trading_reason", "", "Trading reason must be specified"),
        ("timestamp", "not-a-datetime", "Timestamp must be a datetime object"),
    ],
)
def test_trading_signal_validates_metadata(field_name, bad_value, error_message):
    kwargs = _base_signal_kwargs()
    kwargs[field_name] = bad_value
    with pytest.raises(ValueError, match=error_message):
        TradingSignal(**kwargs)


def test_trading_signal_batch_validates_counts():
    signal = TradingSignal(**_base_signal_kwargs())
    with pytest.raises(ValueError, match="must match actual signals count"):
        TradingSignalBatch(
            signals=[signal],
            weather_station="KJFK",
            update_timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
            total_markets_analyzed=3,
            signals_generated=2,
        )


def test_trading_signal_batch_validates_timestamp_and_totals():
    signal = TradingSignal(**_base_signal_kwargs())

    with pytest.raises(TypeError, match="timestamp must be a datetime object"):
        TradingSignalBatch(
            signals=[signal],
            weather_station="KJFK",
            update_timestamp="now",
            total_markets_analyzed=3,
            signals_generated=1,
        )

    with pytest.raises(ValueError, match="cannot be negative"):
        TradingSignalBatch(
            signals=[signal],
            weather_station="KJFK",
            update_timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
            total_markets_analyzed=-1,
            signals_generated=1,
        )


def test_trading_signal_batch_accepts_valid_payload():
    signal = TradingSignal(**_base_signal_kwargs())
    batch = TradingSignalBatch(
        signals=[signal],
        weather_station="KJFK",
        update_timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
        total_markets_analyzed=5,
        signals_generated=1,
    )
    assert batch.weather_station == "KJFK"
    assert batch.signals == [signal]
