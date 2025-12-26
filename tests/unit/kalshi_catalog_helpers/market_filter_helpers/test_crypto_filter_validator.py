"""Tests for crypto_filter_validator module."""

import pytest

from common.kalshi_catalog_helpers.market_filter_helpers.crypto_filter_validator import (
    validate_strike_type,
    validate_strike_values,
    validate_ticker_format,
)


class TestValidateTickerFormat:
    """Tests for validate_ticker_format function."""

    def test_empty_ticker(self) -> None:
        """Test empty ticker is invalid."""
        result = validate_ticker_format("")
        assert result is False

    def test_ticker_without_crypto_asset(self) -> None:
        """Test ticker without crypto asset is invalid."""
        result = validate_ticker_format("WEATHER-24DEC25-T50")
        assert result is False

    def test_ticker_without_month_pattern(self) -> None:
        """Test ticker without month pattern is invalid."""
        result = validate_ticker_format("KXBTC-2024-T50")
        assert result is False

    def test_ticker_with_btc_and_month(self) -> None:
        """Test ticker with BTC and valid month pattern."""
        result = validate_ticker_format("KXBTC-24DEC25-T100000")
        assert isinstance(result, bool)

    def test_ticker_with_eth_and_month(self) -> None:
        """Test ticker with ETH and valid month pattern."""
        result = validate_ticker_format("KXETH-24JAN25-T5000")
        assert isinstance(result, bool)


class TestValidateStrikeType:
    """Tests for validate_strike_type function."""

    def test_greater_type(self) -> None:
        """Test 'greater' strike type is valid."""
        result = validate_strike_type("greater")
        assert result is True

    def test_less_type(self) -> None:
        """Test 'less' strike type is valid."""
        result = validate_strike_type("less")
        assert result is True

    def test_greater_or_equal_type(self) -> None:
        """Test 'greater_or_equal' strike type is valid."""
        result = validate_strike_type("greater_or_equal")
        assert result is True

    def test_less_or_equal_type(self) -> None:
        """Test 'less_or_equal' strike type is valid."""
        result = validate_strike_type("less_or_equal")
        assert result is True

    def test_between_type(self) -> None:
        """Test 'between' strike type is valid."""
        result = validate_strike_type("between")
        assert result is True

    def test_invalid_type(self) -> None:
        """Test invalid strike type."""
        result = validate_strike_type("invalid")
        assert result is False

    def test_none_type(self) -> None:
        """Test None strike type is invalid."""
        result = validate_strike_type(None)
        assert result is False


class TestValidateStrikeValues:
    """Tests for validate_strike_values function."""

    def test_valid_with_cap_strike(self) -> None:
        """Test valid market with cap_strike only."""
        market = {"cap_strike": 100000}
        result = validate_strike_values(market)
        assert result is True

    def test_valid_with_floor_strike(self) -> None:
        """Test valid market with floor_strike only."""
        market = {"floor_strike": 50000}
        result = validate_strike_values(market)
        assert result is True

    def test_valid_with_both_strikes(self) -> None:
        """Test valid market with both strikes."""
        market = {"cap_strike": 100000, "floor_strike": 50000}
        result = validate_strike_values(market)
        assert result is True

    def test_invalid_no_strikes(self) -> None:
        """Test invalid when no strikes present."""
        market = {}
        result = validate_strike_values(market)
        assert result is False

    def test_invalid_both_none(self) -> None:
        """Test invalid when both strikes are None."""
        market = {"cap_strike": None, "floor_strike": None}
        result = validate_strike_values(market)
        assert result is False

    def test_invalid_equal_strikes(self) -> None:
        """Test invalid when strikes are equal."""
        market = {"cap_strike": 100000, "floor_strike": 100000}
        result = validate_strike_values(market)
        assert result is False

    def test_valid_different_strikes(self) -> None:
        """Test valid when strikes are different."""
        market = {"cap_strike": 100000, "floor_strike": 99999}
        result = validate_strike_values(market)
        assert result is True
