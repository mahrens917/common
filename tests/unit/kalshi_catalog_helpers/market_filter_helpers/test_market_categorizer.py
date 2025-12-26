"""Tests for market_categorizer module."""

import pytest

from common.kalshi_catalog_helpers.market_filter_helpers.market_categorizer import (
    create_empty_stats,
    is_valid_market,
)


class TestCreateEmptyStats:
    """Tests for create_empty_stats function."""

    def test_returns_dict_with_expected_keys(self) -> None:
        """Test returns dict with all expected keys."""
        result = create_empty_stats()

        assert "crypto_total" in result
        assert "crypto_kept" in result
        assert "weather_total" in result
        assert "weather_kept" in result
        assert "other_total" in result

    def test_all_values_are_zero(self) -> None:
        """Test all values are initialized to zero."""
        result = create_empty_stats()

        assert result["crypto_total"] == 0
        assert result["crypto_kept"] == 0
        assert result["weather_total"] == 0
        assert result["weather_kept"] == 0
        assert result["other_total"] == 0

    def test_returns_new_dict_each_call(self) -> None:
        """Test returns a new dict each call."""
        result1 = create_empty_stats()
        result2 = create_empty_stats()

        assert result1 is not result2
        result1["crypto_total"] = 5
        assert result2["crypto_total"] == 0


class TestIsValidMarket:
    """Tests for is_valid_market function."""

    def test_valid_market_with_ticker(self) -> None:
        """Test valid market with ticker."""
        market = {"ticker": "BTC-24DEC25-T100"}

        result = is_valid_market(market)

        assert result is True

    def test_valid_market_with_additional_fields(self) -> None:
        """Test valid market with additional fields."""
        market = {
            "ticker": "ETH-24DEC25-T50",
            "status": "active",
            "category": "Crypto",
        }

        result = is_valid_market(market)

        assert result is True

    def test_invalid_not_a_dict(self) -> None:
        """Test invalid when not a dict."""
        result = is_valid_market("not a dict")

        assert result is False

    def test_invalid_none(self) -> None:
        """Test invalid when None."""
        result = is_valid_market(None)

        assert result is False

    def test_invalid_list(self) -> None:
        """Test invalid when list."""
        result = is_valid_market([{"ticker": "BTC"}])

        assert result is False

    def test_invalid_missing_ticker(self) -> None:
        """Test invalid when missing ticker."""
        market = {"status": "active"}

        result = is_valid_market(market)

        assert result is False

    def test_invalid_empty_ticker(self) -> None:
        """Test invalid when ticker is empty string."""
        market = {"ticker": ""}

        result = is_valid_market(market)

        assert result is False

    def test_invalid_none_ticker(self) -> None:
        """Test invalid when ticker is None."""
        market = {"ticker": None}

        result = is_valid_market(market)

        assert result is False

    def test_valid_integer_ticker(self) -> None:
        """Test valid with integer ticker (converted to string)."""
        market = {"ticker": 12345}

        result = is_valid_market(market)

        assert result is True
