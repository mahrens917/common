"""Tests for strike calculator using canonical strike_helpers."""

from src.common.strike_helpers import calculate_strike_value, parse_strike_bounds


class TestCalculateStrikeValue:
    """Tests for calculate_strike_value function."""

    def test_between_calculates_midpoint(self) -> None:
        """Returns midpoint for 'between' type with both values."""
        result = calculate_strike_value("between", 40.0, 50.0)

        assert result == 45.0

    def test_between_returns_none_if_floor_missing(self) -> None:
        """Returns None for 'between' type if floor is None."""
        result = calculate_strike_value("between", None, 50.0)

        assert result is None

    def test_between_returns_none_if_cap_missing(self) -> None:
        """Returns None for 'between' type if cap is None."""
        result = calculate_strike_value("between", 40.0, None)

        assert result is None

    def test_greater_returns_floor(self) -> None:
        """Returns floor value for 'greater' type."""
        result = calculate_strike_value("greater", 40.0, 50.0)

        assert result == 40.0

    def test_greater_returns_none_if_floor_missing(self) -> None:
        """Returns None for 'greater' type if floor is None."""
        result = calculate_strike_value("greater", None, 50.0)

        assert result is None

    def test_less_returns_cap(self) -> None:
        """Returns cap value for 'less' type."""
        result = calculate_strike_value("less", 40.0, 50.0)

        assert result == 50.0

    def test_less_returns_none_if_cap_missing(self) -> None:
        """Returns None for 'less' type if cap is None."""
        result = calculate_strike_value("less", 40.0, None)

        assert result is None

    def test_unknown_type_returns_none(self) -> None:
        """Returns None for unknown strike type."""
        result = calculate_strike_value("unknown", 40.0, 50.0)

        assert result is None


class TestParseStrikeBounds:
    """Tests for parse_strike_bounds function."""

    def test_parses_valid_floats(self) -> None:
        """Parses valid float values."""
        floor_value, cap_value = parse_strike_bounds("40.5", "50.5")

        assert floor_value == 40.5
        assert cap_value == 50.5

    def test_parses_valid_integers(self) -> None:
        """Parses valid integer values as floats."""
        floor_value, cap_value = parse_strike_bounds(40, 50)

        assert floor_value == 40.0
        assert cap_value == 50.0

    def test_returns_none_for_none_values(self) -> None:
        """Returns None for None input values."""
        floor_value, cap_value = parse_strike_bounds(None, None)

        assert floor_value is None
        assert cap_value is None

    def test_returns_none_for_empty_strings(self) -> None:
        """Returns None for empty string values."""
        floor_value, cap_value = parse_strike_bounds("", "")

        assert floor_value is None
        assert cap_value is None

    def test_handles_mixed_valid_and_none(self) -> None:
        """Handles mix of valid value and None."""
        floor_value, cap_value = parse_strike_bounds("40.0", None)

        assert floor_value == 40.0
        assert cap_value is None
