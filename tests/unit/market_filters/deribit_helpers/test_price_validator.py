"""Tests for price validator module."""

from src.common.market_filters.deribit_helpers.price_validator import PriceValidator


class TestPriceValidatorValidateQuotes:
    """Tests for PriceValidator.validate_quotes."""

    def test_validate_quotes_returns_none_when_valid(self) -> None:
        """Returns None when quotes are valid."""
        result = PriceValidator.validate_quotes(100.0, 101.0, 0.1)

        assert result is None

    def test_validate_quotes_returns_missing_when_bid_none(self) -> None:
        """Returns 'missing_quotes' when bid is None."""
        result = PriceValidator.validate_quotes(None, 101.0, 0.1)

        assert result == "missing_quotes"

    def test_validate_quotes_returns_missing_when_ask_none(self) -> None:
        """Returns 'missing_quotes' when ask is None."""
        result = PriceValidator.validate_quotes(100.0, None, 0.1)

        assert result == "missing_quotes"

    def test_validate_quotes_returns_invalid_when_bid_zero(self) -> None:
        """Returns 'invalid_price' when bid is zero."""
        result = PriceValidator.validate_quotes(0, 101.0, 0.1)

        assert result == "invalid_price"

    def test_validate_quotes_returns_invalid_when_ask_zero(self) -> None:
        """Returns 'invalid_price' when ask is zero."""
        result = PriceValidator.validate_quotes(100.0, 0, 0.1)

        assert result == "invalid_price"

    def test_validate_quotes_returns_invalid_when_bid_negative(self) -> None:
        """Returns 'invalid_price' when bid is negative."""
        result = PriceValidator.validate_quotes(-100.0, 101.0, 0.1)

        assert result == "invalid_price"

    def test_validate_quotes_returns_invalid_spread_when_ask_less(self) -> None:
        """Returns 'invalid_spread' when ask is less than bid."""
        result = PriceValidator.validate_quotes(100.0, 99.0, 0.1)

        assert result == "invalid_spread"

    def test_validate_quotes_returns_invalid_spread_when_equal(self) -> None:
        """Returns 'invalid_spread' when ask equals bid."""
        result = PriceValidator.validate_quotes(100.0, 100.0, 0.1)

        assert result == "invalid_spread"

    def test_validate_quotes_returns_wide_spread_when_too_wide(self) -> None:
        """Returns 'wide_spread' when relative spread exceeds max."""
        result = PriceValidator.validate_quotes(100.0, 120.0, 0.1)

        assert result == "wide_spread"

    def test_validate_quotes_accepts_tight_spread(self) -> None:
        """Accepts quotes with tight spread."""
        result = PriceValidator.validate_quotes(100.0, 100.5, 0.1)

        assert result is None

    def test_validate_quotes_accepts_spread_at_max(self) -> None:
        """Accepts spread exactly at maximum."""
        result = PriceValidator.validate_quotes(100.0, 110.0, 0.1)

        assert result is None
