"""Tests for trading signals validation."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from common.data_models.trading_signals_helpers.validation import (
    ERR_BUY_SELL_MISSING_FIELDS,
    ERR_NO_TRADE_HAS_TRADE_FIELDS,
    ERR_TARGET_PRICE_OUT_OF_RANGE,
    ERR_TICKER_REQUIRED,
    ERR_TIMESTAMP_NOT_DATETIME_SIG,
    ERR_TRADING_REASON_REQUIRED,
    ERR_WEATHER_REASON_REQUIRED,
    _validate_no_trade_signal,
    _validate_required_fields,
    _validate_trade_signal_fields,
    validate_trading_signal,
)


class TestValidateTradingSignal:
    """Tests for validate_trading_signal function."""

    def test_validates_buy_signal(self) -> None:
        """Validates BUY signal fields."""
        from common.data_models.trading_signals import TradingSignalType

        signal = MagicMock()
        signal.signal_type = TradingSignalType.BUY
        signal.action = MagicMock()
        signal.side = MagicMock()
        signal.target_price_cents = 50
        signal.ticker = "TEST-TICKER"
        signal.weather_reason = "Weather reason"
        signal.trading_reason = "Trading reason"
        signal.timestamp = datetime.now()

        validate_trading_signal(signal)

    def test_validates_sell_signal(self) -> None:
        """Validates SELL signal fields."""
        from common.data_models.trading_signals import TradingSignalType

        signal = MagicMock()
        signal.signal_type = TradingSignalType.SELL
        signal.action = MagicMock()
        signal.side = MagicMock()
        signal.target_price_cents = 50
        signal.ticker = "TEST-TICKER"
        signal.weather_reason = "Weather reason"
        signal.trading_reason = "Trading reason"
        signal.timestamp = datetime.now()

        validate_trading_signal(signal)

    def test_validates_no_trade_signal(self) -> None:
        """Validates NO_TRADE signal fields."""
        from common.data_models.trading_signals import TradingSignalType

        signal = MagicMock()
        signal.signal_type = TradingSignalType.NO_TRADE
        signal.action = None
        signal.side = None
        signal.target_price_cents = None
        signal.ticker = "TEST-TICKER"
        signal.weather_reason = "Weather reason"
        signal.trading_reason = "Trading reason"
        signal.timestamp = datetime.now()

        validate_trading_signal(signal)


class TestValidateTradeSignalFields:
    """Tests for _validate_trade_signal_fields function."""

    def test_raises_when_action_missing(self) -> None:
        """Raises ValueError when action is missing."""
        signal = MagicMock()
        signal.action = None
        signal.side = MagicMock()
        signal.target_price_cents = 50

        with pytest.raises(ValueError, match=ERR_BUY_SELL_MISSING_FIELDS):
            _validate_trade_signal_fields(signal)

    def test_raises_when_side_missing(self) -> None:
        """Raises ValueError when side is missing."""
        signal = MagicMock()
        signal.action = MagicMock()
        signal.side = None
        signal.target_price_cents = 50

        with pytest.raises(ValueError, match=ERR_BUY_SELL_MISSING_FIELDS):
            _validate_trade_signal_fields(signal)

    def test_raises_when_target_price_missing(self) -> None:
        """Raises ValueError when target_price_cents is missing."""
        signal = MagicMock()
        signal.action = MagicMock()
        signal.side = MagicMock()
        signal.target_price_cents = None

        with pytest.raises(ValueError, match=ERR_BUY_SELL_MISSING_FIELDS):
            _validate_trade_signal_fields(signal)

    def test_raises_when_target_price_zero(self) -> None:
        """Raises ValidationError when target_price is zero."""
        from common.exceptions import ValidationError

        signal = MagicMock()
        signal.action = MagicMock()
        signal.side = MagicMock()
        signal.target_price_cents = 0

        with pytest.raises(ValidationError, match="Target price must be between"):
            _validate_trade_signal_fields(signal)

    def test_raises_when_target_price_negative(self) -> None:
        """Raises ValidationError when target_price is negative."""
        from common.exceptions import ValidationError

        signal = MagicMock()
        signal.action = MagicMock()
        signal.side = MagicMock()
        signal.target_price_cents = -10

        with pytest.raises(ValidationError, match="Target price must be between"):
            _validate_trade_signal_fields(signal)

    def test_raises_when_target_price_exceeds_max(self) -> None:
        """Raises ValidationError when target_price exceeds max."""
        from common.exceptions import ValidationError

        signal = MagicMock()
        signal.action = MagicMock()
        signal.side = MagicMock()
        signal.target_price_cents = 200  # Exceeds max

        with pytest.raises(ValidationError, match="Target price must be between"):
            _validate_trade_signal_fields(signal)

    def test_valid_trade_signal_passes(self) -> None:
        """Valid trade signal passes validation."""
        signal = MagicMock()
        signal.action = MagicMock()
        signal.side = MagicMock()
        signal.target_price_cents = 50

        _validate_trade_signal_fields(signal)


class TestValidateNoTradeSignal:
    """Tests for _validate_no_trade_signal function."""

    def test_raises_when_action_present(self) -> None:
        """Raises ValueError when action is present."""
        signal = MagicMock()
        signal.action = MagicMock()
        signal.side = None
        signal.target_price_cents = None

        with pytest.raises(ValueError, match=ERR_NO_TRADE_HAS_TRADE_FIELDS):
            _validate_no_trade_signal(signal)

    def test_raises_when_side_present(self) -> None:
        """Raises ValueError when side is present."""
        signal = MagicMock()
        signal.action = None
        signal.side = MagicMock()
        signal.target_price_cents = None

        with pytest.raises(ValueError, match=ERR_NO_TRADE_HAS_TRADE_FIELDS):
            _validate_no_trade_signal(signal)

    def test_raises_when_target_price_present(self) -> None:
        """Raises ValueError when target_price_cents is present."""
        signal = MagicMock()
        signal.action = None
        signal.side = None
        signal.target_price_cents = 50

        with pytest.raises(ValueError, match=ERR_NO_TRADE_HAS_TRADE_FIELDS):
            _validate_no_trade_signal(signal)

    def test_valid_no_trade_signal_passes(self) -> None:
        """Valid no trade signal passes validation."""
        signal = MagicMock()
        signal.action = None
        signal.side = None
        signal.target_price_cents = None

        _validate_no_trade_signal(signal)


class TestValidateRequiredFields:
    """Tests for _validate_required_fields function."""

    def test_raises_when_ticker_missing(self) -> None:
        """Raises TypeError when ticker is missing."""
        signal = MagicMock()
        signal.ticker = ""
        signal.weather_reason = "Weather reason"
        signal.trading_reason = "Trading reason"
        signal.timestamp = datetime.now()

        with pytest.raises(TypeError, match=ERR_TICKER_REQUIRED):
            _validate_required_fields(signal)

    def test_raises_when_ticker_none(self) -> None:
        """Raises TypeError when ticker is None."""
        signal = MagicMock()
        signal.ticker = None
        signal.weather_reason = "Weather reason"
        signal.trading_reason = "Trading reason"
        signal.timestamp = datetime.now()

        with pytest.raises(TypeError, match=ERR_TICKER_REQUIRED):
            _validate_required_fields(signal)

    def test_raises_when_weather_reason_missing(self) -> None:
        """Raises TypeError when weather_reason is missing."""
        signal = MagicMock()
        signal.ticker = "TEST-TICKER"
        signal.weather_reason = ""
        signal.trading_reason = "Trading reason"
        signal.timestamp = datetime.now()

        with pytest.raises(TypeError, match=ERR_WEATHER_REASON_REQUIRED):
            _validate_required_fields(signal)

    def test_raises_when_trading_reason_missing(self) -> None:
        """Raises TypeError when trading_reason is missing."""
        signal = MagicMock()
        signal.ticker = "TEST-TICKER"
        signal.weather_reason = "Weather reason"
        signal.trading_reason = ""
        signal.timestamp = datetime.now()

        with pytest.raises(TypeError, match=ERR_TRADING_REASON_REQUIRED):
            _validate_required_fields(signal)

    def test_raises_when_timestamp_not_datetime(self) -> None:
        """Raises TypeError when timestamp is not datetime."""
        signal = MagicMock()
        signal.ticker = "TEST-TICKER"
        signal.weather_reason = "Weather reason"
        signal.trading_reason = "Trading reason"
        signal.timestamp = "2025-01-01"

        with pytest.raises(TypeError, match=ERR_TIMESTAMP_NOT_DATETIME_SIG):
            _validate_required_fields(signal)

    def test_valid_required_fields_passes(self) -> None:
        """Valid required fields pass validation."""
        signal = MagicMock()
        signal.ticker = "TEST-TICKER"
        signal.weather_reason = "Weather reason"
        signal.trading_reason = "Trading reason"
        signal.timestamp = datetime.now()

        _validate_required_fields(signal)
