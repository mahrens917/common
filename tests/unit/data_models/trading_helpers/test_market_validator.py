"""Tests for market validator module."""

from datetime import datetime

import pytest

from src.common.data_models.trading_helpers.market_validator import (
    validate_ask_price,
    validate_bid_ask_spread,
    validate_bid_price,
    validate_last_price,
    validate_market_open_status,
    validate_market_ticker,
    validate_market_timestamp,
    validate_market_validation_data,
)


class TestValidateMarketTicker:
    """Tests for validate_market_ticker function."""

    def test_valid_ticker(self) -> None:
        """Accepts valid ticker."""
        validate_market_ticker("KXBTC-25JAN01")

    def test_empty_ticker_raises(self) -> None:
        """Raises ValueError for empty ticker."""
        with pytest.raises(ValueError) as exc_info:
            validate_market_ticker("")

        assert "Ticker must be specified" in str(exc_info.value)


class TestValidateMarketOpenStatus:
    """Tests for validate_market_open_status function."""

    def test_valid_true(self) -> None:
        """Accepts True."""
        validate_market_open_status(True)

    def test_valid_false(self) -> None:
        """Accepts False."""
        validate_market_open_status(False)

    def test_non_bool_raises(self) -> None:
        """Raises TypeError for non-boolean."""
        with pytest.raises(TypeError) as exc_info:
            validate_market_open_status("true")

        assert "boolean" in str(exc_info.value)


class TestValidateBidPrice:
    """Tests for validate_bid_price function."""

    def test_valid_price(self) -> None:
        """Accepts valid bid price."""
        validate_bid_price(50)

    def test_none_price_accepted(self) -> None:
        """Accepts None bid price."""
        validate_bid_price(None)

    def test_zero_price_raises(self) -> None:
        """Raises ValueError for zero price."""
        with pytest.raises(ValueError) as exc_info:
            validate_bid_price(0)

        assert "1-99 cents" in str(exc_info.value)

    def test_over_99_raises(self) -> None:
        """Raises ValueError for price > 99."""
        with pytest.raises(ValueError) as exc_info:
            validate_bid_price(100)

        assert "1-99 cents" in str(exc_info.value)


class TestValidateAskPrice:
    """Tests for validate_ask_price function."""

    def test_valid_price(self) -> None:
        """Accepts valid ask price."""
        validate_ask_price(50)

    def test_none_price_accepted(self) -> None:
        """Accepts None ask price."""
        validate_ask_price(None)

    def test_zero_price_raises(self) -> None:
        """Raises ValueError for zero price."""
        with pytest.raises(ValueError) as exc_info:
            validate_ask_price(0)

        assert "1-99 cents" in str(exc_info.value)

    def test_over_99_raises(self) -> None:
        """Raises ValueError for price > 99."""
        with pytest.raises(ValueError) as exc_info:
            validate_ask_price(100)

        assert "1-99 cents" in str(exc_info.value)


class TestValidateBidAskSpread:
    """Tests for validate_bid_ask_spread function."""

    def test_valid_spread(self) -> None:
        """Accepts valid bid < ask."""
        validate_bid_ask_spread(40, 50)

    def test_none_bid_accepted(self) -> None:
        """Accepts None bid."""
        validate_bid_ask_spread(None, 50)

    def test_none_ask_accepted(self) -> None:
        """Accepts None ask."""
        validate_bid_ask_spread(40, None)

    def test_equal_prices_raises(self) -> None:
        """Raises ValueError when bid == ask."""
        with pytest.raises(ValueError) as exc_info:
            validate_bid_ask_spread(50, 50)

        assert "less than best ask" in str(exc_info.value)

    def test_bid_greater_raises(self) -> None:
        """Raises ValueError when bid > ask."""
        with pytest.raises(ValueError) as exc_info:
            validate_bid_ask_spread(60, 50)

        assert "less than best ask" in str(exc_info.value)


class TestValidateLastPrice:
    """Tests for validate_last_price function."""

    def test_valid_price(self) -> None:
        """Accepts valid last price."""
        validate_last_price(50)

    def test_none_price_accepted(self) -> None:
        """Accepts None last price."""
        validate_last_price(None)

    def test_zero_price_raises(self) -> None:
        """Raises ValueError for zero price."""
        with pytest.raises(ValueError) as exc_info:
            validate_last_price(0)

        assert "1-99 cents" in str(exc_info.value)


class TestValidateMarketTimestamp:
    """Tests for validate_market_timestamp function."""

    def test_valid_timestamp(self) -> None:
        """Accepts valid datetime."""
        validate_market_timestamp(datetime.now())

    def test_string_raises(self) -> None:
        """Raises TypeError for string."""
        with pytest.raises(TypeError) as exc_info:
            validate_market_timestamp("2024-01-01")

        assert "datetime object" in str(exc_info.value)


class TestValidateMarketValidationData:
    """Tests for validate_market_validation_data function."""

    def test_valid_complete_data(self) -> None:
        """Accepts valid complete market data."""
        validate_market_validation_data(
            ticker="KXBTC-25JAN01",
            is_open=True,
            best_bid_cents=40,
            best_ask_cents=50,
            last_price_cents=45,
            timestamp=datetime.now(),
        )

    def test_valid_with_none_prices(self) -> None:
        """Accepts valid data with None prices."""
        validate_market_validation_data(
            ticker="KXBTC-25JAN01",
            is_open=True,
            best_bid_cents=None,
            best_ask_cents=None,
            last_price_cents=None,
            timestamp=datetime.now(),
        )

    def test_invalid_ticker_propagates(self) -> None:
        """Propagates ticker validation error."""
        with pytest.raises(ValueError):
            validate_market_validation_data(
                ticker="",
                is_open=True,
                best_bid_cents=40,
                best_ask_cents=50,
                last_price_cents=45,
                timestamp=datetime.now(),
            )
