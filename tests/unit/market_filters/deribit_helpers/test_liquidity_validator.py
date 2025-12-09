"""Tests for liquidity validator module."""

from src.common.market_filters.deribit_helpers.liquidity_validator import LiquidityValidator


class TestLiquidityValidatorValidateSizes:
    """Tests for LiquidityValidator.validate_sizes."""

    def test_validate_sizes_returns_none_when_valid(self) -> None:
        """Returns None when both sizes exceed minimum."""
        result = LiquidityValidator.validate_sizes(10.0, 15.0, 5.0)

        assert result is None

    def test_validate_sizes_returns_missing_when_bid_is_none(self) -> None:
        """Returns 'missing_liquidity' when bid_size is None."""
        result = LiquidityValidator.validate_sizes(None, 15.0, 5.0)

        assert result == "missing_liquidity"

    def test_validate_sizes_returns_missing_when_ask_is_none(self) -> None:
        """Returns 'missing_liquidity' when ask_size is None."""
        result = LiquidityValidator.validate_sizes(10.0, None, 5.0)

        assert result == "missing_liquidity"

    def test_validate_sizes_returns_missing_when_bid_below_min(self) -> None:
        """Returns 'missing_liquidity' when bid_size is below minimum."""
        result = LiquidityValidator.validate_sizes(3.0, 15.0, 5.0)

        assert result == "missing_liquidity"

    def test_validate_sizes_returns_missing_when_ask_below_min(self) -> None:
        """Returns 'missing_liquidity' when ask_size is below minimum."""
        result = LiquidityValidator.validate_sizes(10.0, 3.0, 5.0)

        assert result == "missing_liquidity"

    def test_validate_sizes_returns_missing_when_bid_equals_min(self) -> None:
        """Returns 'missing_liquidity' when bid_size equals minimum."""
        result = LiquidityValidator.validate_sizes(5.0, 15.0, 5.0)

        assert result == "missing_liquidity"

    def test_validate_sizes_returns_missing_when_ask_equals_min(self) -> None:
        """Returns 'missing_liquidity' when ask_size equals minimum."""
        result = LiquidityValidator.validate_sizes(10.0, 5.0, 5.0)

        assert result == "missing_liquidity"

    def test_validate_sizes_with_zero_minimum(self) -> None:
        """Works with zero as minimum liquidity."""
        result = LiquidityValidator.validate_sizes(0.001, 0.001, 0.0)

        assert result is None

    def test_validate_sizes_returns_missing_when_both_none(self) -> None:
        """Returns 'missing_liquidity' when both sizes are None."""
        result = LiquidityValidator.validate_sizes(None, None, 5.0)

        assert result == "missing_liquidity"
