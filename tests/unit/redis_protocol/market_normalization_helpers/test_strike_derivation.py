"""Tests for strike derivation module."""

from unittest.mock import patch

from src.common.redis_protocol.market_normalization_helpers.strike_derivation import (
    StrikeDerivation,
)


class TestStrikeDerivationDetermineKeywordType:
    """Tests for StrikeDerivation.determine_keyword_type."""

    def test_between_keyword(self) -> None:
        """Returns 'between' for BETWEEN token."""
        tokens = ["KXBTC", "BETWEEN", "50000", "60000"]

        result = StrikeDerivation.determine_keyword_type(tokens)

        assert result == "between"

    def test_less_keyword(self) -> None:
        """Returns 'less' for LESS token."""
        tokens = ["KXBTC", "LESS", "50000"]

        result = StrikeDerivation.determine_keyword_type(tokens)

        assert result == "less"

    def test_below_keyword(self) -> None:
        """Returns 'less' for BELOW token."""
        tokens = ["KXBTC", "BELOW", "50000"]

        result = StrikeDerivation.determine_keyword_type(tokens)

        assert result == "less"

    def test_greater_keyword(self) -> None:
        """Returns 'greater' for GREATER token."""
        tokens = ["KXBTC", "GREATER", "50000"]

        result = StrikeDerivation.determine_keyword_type(tokens)

        assert result == "greater"

    def test_above_keyword(self) -> None:
        """Returns 'greater' for ABOVE token."""
        tokens = ["KXBTC", "ABOVE", "50000"]

        result = StrikeDerivation.determine_keyword_type(tokens)

        assert result == "greater"

    def test_no_keyword(self) -> None:
        """Returns None for no keyword."""
        tokens = ["KXBTC", "50000"]

        result = StrikeDerivation.determine_keyword_type(tokens)

        assert result is None


class TestStrikeDerivationApplyPrefixBounds:
    """Tests for StrikeDerivation.apply_prefix_bounds."""

    def test_b_prefix_sets_cap(self) -> None:
        """B prefix sets cap strike."""
        floor, cap = StrikeDerivation.apply_prefix_bounds("B", "between", 50000.0, None, None)

        assert cap == 50000.0
        assert floor is None

    def test_t_prefix_sets_floor(self) -> None:
        """T prefix sets floor strike."""
        floor, cap = StrikeDerivation.apply_prefix_bounds("T", "between", 50000.0, None, None)

        assert floor == 50000.0
        assert cap is None

    def test_greater_type_sets_floor(self) -> None:
        """Greater type sets floor when prefix doesn't match."""
        floor, cap = StrikeDerivation.apply_prefix_bounds("X", "greater", 50000.0, None, None)

        assert floor == 50000.0
        assert cap is None


class TestStrikeDerivationHandleBetweenType:
    """Tests for StrikeDerivation.handle_between_type."""

    def test_returns_between_type(self) -> None:
        """Returns 'between' as strike type."""
        with patch(
            "src.common.redis_protocol.market_normalization_helpers.strike_derivation.extract_between_bounds"
        ) as mock_extract:
            with patch(
                "src.common.redis_protocol.market_normalization_helpers.strike_derivation.compute_representative_strike"
            ) as mock_compute:
                mock_extract.return_value = (50000.0, 60000.0)
                mock_compute.return_value = 55000.0

                result = StrikeDerivation.handle_between_type(
                    ["BETWEEN", "50000", "60000"], None, None, 55000.0
                )

                assert result[0] == "between"
                assert result[1] == 50000.0
                assert result[2] == 60000.0
                assert result[3] == 55000.0


class TestStrikeDerivationFinalizeBounds:
    """Tests for StrikeDerivation.finalize_bounds."""

    def test_less_type_sets_cap(self) -> None:
        """Less type sets cap strike."""
        floor, cap = StrikeDerivation.finalize_bounds("less", 50000.0, None, None)

        assert cap == 50000.0
        assert floor is None

    def test_greater_type_sets_floor(self) -> None:
        """Greater type sets floor strike."""
        floor, cap = StrikeDerivation.finalize_bounds("greater", 50000.0, None, None)

        assert floor == 50000.0
        assert cap is None

    def test_preserves_existing_cap(self) -> None:
        """Preserves existing cap strike."""
        floor, cap = StrikeDerivation.finalize_bounds("less", 60000.0, None, 50000.0)

        assert cap == 50000.0

    def test_preserves_existing_floor(self) -> None:
        """Preserves existing floor strike."""
        floor, cap = StrikeDerivation.finalize_bounds("greater", 60000.0, 50000.0, None)

        assert floor == 50000.0
