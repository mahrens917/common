"""Tests for strike bounds builder module."""

from common.redis_protocol.market_normalization_helpers.strike_bounds_builder import (
    apply_prefix_bounds,
    determine_keyword_type,
    finalize_bounds,
)


class TestDetermineKeywordType:
    """Tests for determine_keyword_type function."""

    def test_between_keyword(self) -> None:
        """Returns 'between' for BETWEEN token."""
        tokens = ["KXBTC", "BETWEEN", "50000", "60000"]

        result = determine_keyword_type(tokens)

        assert result == "between"

    def test_less_keyword(self) -> None:
        """Returns 'less' for LESS token."""
        tokens = ["KXBTC", "LESS", "50000"]

        result = determine_keyword_type(tokens)

        assert result == "less"

    def test_below_keyword(self) -> None:
        """Returns 'less' for BELOW token."""
        tokens = ["KXBTC", "BELOW", "50000"]

        result = determine_keyword_type(tokens)

        assert result == "less"

    def test_greater_keyword(self) -> None:
        """Returns 'greater' for GREATER token."""
        tokens = ["KXBTC", "GREATER", "50000"]

        result = determine_keyword_type(tokens)

        assert result == "greater"

    def test_above_keyword(self) -> None:
        """Returns 'greater' for ABOVE token."""
        tokens = ["KXBTC", "ABOVE", "50000"]

        result = determine_keyword_type(tokens)

        assert result == "greater"

    def test_no_keyword(self) -> None:
        """Returns None for no keyword."""
        tokens = ["KXBTC", "50000"]

        result = determine_keyword_type(tokens)

        assert result is None


class TestApplyPrefixBounds:
    """Tests for apply_prefix_bounds function."""

    def test_b_prefix_sets_cap(self) -> None:
        """B prefix sets cap strike."""
        floor, cap = apply_prefix_bounds("B", "between", 50000.0, None, None)

        assert cap == 50000.0
        assert floor is None

    def test_t_prefix_sets_floor(self) -> None:
        """T prefix sets floor strike."""
        floor, cap = apply_prefix_bounds("T", "between", 50000.0, None, None)

        assert floor == 50000.0
        assert cap is None

    def test_greater_type_sets_floor(self) -> None:
        """Greater type sets floor when prefix doesn't match."""
        floor, cap = apply_prefix_bounds("X", "greater", 50000.0, None, None)

        assert floor == 50000.0
        assert cap is None

    def test_preserves_existing_floor(self) -> None:
        """Preserves existing floor strike."""
        floor, cap = apply_prefix_bounds("X", "greater", 60000.0, 50000.0, None)

        assert floor == 50000.0

    def test_lowercase_b_prefix(self) -> None:
        """Handles lowercase b prefix."""
        floor, cap = apply_prefix_bounds("b", "between", 50000.0, None, None)

        assert cap == 50000.0


class TestFinalizeBounds:
    """Tests for finalize_bounds function."""

    def test_less_type_sets_cap(self) -> None:
        """Less type sets cap strike."""
        floor, cap = finalize_bounds("less", 50000.0, None, None)

        assert cap == 50000.0
        assert floor is None

    def test_greater_type_sets_floor(self) -> None:
        """Greater type sets floor strike."""
        floor, cap = finalize_bounds("greater", 50000.0, None, None)

        assert floor == 50000.0
        assert cap is None

    def test_preserves_existing_cap(self) -> None:
        """Preserves existing cap strike."""
        floor, cap = finalize_bounds("less", 60000.0, None, 50000.0)

        assert cap == 50000.0

    def test_preserves_existing_floor(self) -> None:
        """Preserves existing floor strike."""
        floor, cap = finalize_bounds("greater", 60000.0, 50000.0, None)

        assert floor == 50000.0
