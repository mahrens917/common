"""Tests for portfolio validator module."""

from datetime import datetime
from enum import Enum

import pytest

from common.data_models.trading_helpers.portfolio_validator import (
    validate_portfolio_balance,
    validate_portfolio_position,
    validate_position_count,
    validate_position_price,
    validate_position_side,
    validate_position_ticker,
    validate_position_timestamp,
)


class TestValidatePortfolioBalance:
    """Tests for validate_portfolio_balance function."""

    def test_valid_balance(self) -> None:
        """Accepts valid balance."""
        validate_portfolio_balance(10000, "USD", datetime.now())

    def test_zero_balance_accepted(self) -> None:
        """Accepts zero balance."""
        validate_portfolio_balance(0, "USD", datetime.now())

    def test_negative_balance_raises(self) -> None:
        """Raises ValueError for negative balance."""
        with pytest.raises(ValueError) as exc_info:
            validate_portfolio_balance(-100, "USD", datetime.now())

        assert "cannot be negative" in str(exc_info.value)

    def test_empty_currency_raises(self) -> None:
        """Raises ValueError for empty currency."""
        with pytest.raises(ValueError) as exc_info:
            validate_portfolio_balance(10000, "", datetime.now())

        assert "Currency must be specified" in str(exc_info.value)

    def test_non_usd_currency_raises(self) -> None:
        """Raises ValueError for non-USD currency."""
        with pytest.raises(ValueError) as exc_info:
            validate_portfolio_balance(10000, "EUR", datetime.now())

        assert "Only USD currency supported" in str(exc_info.value)

    def test_invalid_timestamp_raises(self) -> None:
        """Raises TypeError for invalid timestamp."""
        with pytest.raises(TypeError) as exc_info:
            validate_portfolio_balance(10000, "USD", "2024-01-01")

        assert "datetime object" in str(exc_info.value)


class TestValidatePositionTicker:
    """Tests for validate_position_ticker function."""

    def test_valid_ticker(self) -> None:
        """Accepts valid ticker."""
        validate_position_ticker("KXBTC-25JAN01")

    def test_empty_ticker_raises(self) -> None:
        """Raises ValueError for empty ticker."""
        with pytest.raises(ValueError) as exc_info:
            validate_position_ticker("")

        assert "Ticker must be specified" in str(exc_info.value)


class TestValidatePositionCount:
    """Tests for validate_position_count function."""

    def test_valid_positive_count(self) -> None:
        """Accepts positive count."""
        validate_position_count(10)

    def test_valid_negative_count(self) -> None:
        """Accepts negative count (short position)."""
        validate_position_count(-10)

    def test_zero_count_raises(self) -> None:
        """Raises ValueError for zero count."""
        with pytest.raises(ValueError) as exc_info:
            validate_position_count(0)

        assert "cannot be zero" in str(exc_info.value)


class TestValidatePositionSide:
    """Tests for validate_position_side function."""

    def test_valid_side(self) -> None:
        """Accepts valid OrderSide enum."""
        from common.data_models.trading import OrderSide

        validate_position_side(OrderSide.YES)

    def test_invalid_side_raises(self) -> None:
        """Raises TypeError for non-OrderSide."""
        with pytest.raises(TypeError) as exc_info:
            validate_position_side("YES")

        assert "OrderSide enum" in str(exc_info.value)


class TestValidatePositionPrice:
    """Tests for validate_position_price function."""

    def test_valid_price(self) -> None:
        """Accepts valid price."""
        validate_position_price(50)

    def test_price_of_100_accepted(self) -> None:
        """Accepts price of 100."""
        validate_position_price(100)

    def test_zero_price_raises(self) -> None:
        """Raises ValueError for zero price."""
        with pytest.raises(ValueError) as exc_info:
            validate_position_price(0)

        assert "1-100 cents" in str(exc_info.value)

    def test_over_100_raises(self) -> None:
        """Raises ValueError for price > 100."""
        with pytest.raises(ValueError) as exc_info:
            validate_position_price(101)

        assert "1-100 cents" in str(exc_info.value)


class TestValidatePositionTimestamp:
    """Tests for validate_position_timestamp function."""

    def test_valid_timestamp(self) -> None:
        """Accepts valid datetime."""
        validate_position_timestamp(datetime.now())

    def test_invalid_timestamp_raises(self) -> None:
        """Raises TypeError for invalid timestamp."""
        with pytest.raises(TypeError) as exc_info:
            validate_position_timestamp("2024-01-01")

        assert "datetime object" in str(exc_info.value)


class TestValidatePortfolioPosition:
    """Tests for validate_portfolio_position function."""

    def test_valid_complete_position(self) -> None:
        """Accepts valid complete position."""
        from common.data_models.trading import OrderSide

        validate_portfolio_position(
            ticker="KXBTC-25JAN01",
            position_count=10,
            side=OrderSide.YES,
            average_price_cents=50,
            last_updated=datetime.now(),
        )

    def test_invalid_ticker_propagates(self) -> None:
        """Propagates ticker validation error."""
        from common.data_models.trading import OrderSide

        with pytest.raises(ValueError) as exc_info:
            validate_portfolio_position(
                ticker="",
                position_count=10,
                side=OrderSide.YES,
                average_price_cents=50,
                last_updated=datetime.now(),
            )

        assert "Ticker" in str(exc_info.value)
