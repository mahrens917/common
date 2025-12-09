"""Tests for strike parser module."""

from src.common.strike_helpers import (
    compute_representative_strike,
    extract_between_bounds,
    parse_strike_segment,
    resolve_strike_type_from_prefix,
)


class TestParseStrikeSegment:
    """Tests for parse_strike_segment function."""

    def test_returns_empty_for_empty_string(self) -> None:
        """Returns empty strings for empty input."""
        prefix, value_str = parse_strike_segment("")

        assert prefix == ""
        assert value_str == ""

    def test_extracts_alpha_prefix(self) -> None:
        """Extracts alphabetic prefix."""
        prefix, value_str = parse_strike_segment("B50000")

        assert prefix == "B"
        assert value_str == "50000"

    def test_no_prefix_for_numeric_start(self) -> None:
        """No prefix extraction for numeric start."""
        prefix, value_str = parse_strike_segment("50000")

        assert prefix == "5"
        assert value_str == "50000"

    def test_lowercase_prefix(self) -> None:
        """Handles lowercase prefix."""
        prefix, value_str = parse_strike_segment("t60000")

        assert prefix == "t"
        assert value_str == "60000"

    def test_single_character(self) -> None:
        """Handles single character input."""
        prefix, value_str = parse_strike_segment("B")

        assert prefix == "B"
        assert value_str == ""


class TestResolveStrikeTypeFromPrefix:
    """Tests for resolve_strike_type_from_prefix function."""

    def test_b_prefix_returns_less(self) -> None:
        """B prefix returns less type."""
        strike_type, floor, cap = resolve_strike_type_from_prefix("B", None)

        assert strike_type == "less"
        assert floor is None
        assert cap is None

    def test_t_prefix_returns_greater(self) -> None:
        """T prefix returns greater type."""
        strike_type, floor, cap = resolve_strike_type_from_prefix("T", None)

        assert strike_type == "greater"
        assert floor is None
        assert cap is None

    def test_m_prefix_returns_between(self) -> None:
        """M prefix returns between type."""
        strike_type, floor, cap = resolve_strike_type_from_prefix("M", None)

        assert strike_type == "between"
        assert floor is None
        assert cap is None

    def test_lowercase_b_prefix(self) -> None:
        """Lowercase b prefix returns less type."""
        strike_type, floor, cap = resolve_strike_type_from_prefix("b", None)

        assert strike_type == "less"

    def test_uses_keyword_type_when_no_match(self) -> None:
        """Uses keyword_type when prefix doesn't match."""
        strike_type, floor, cap = resolve_strike_type_from_prefix("X", "between")

        assert strike_type == "between"

    def test_defaults_to_greater(self) -> None:
        """Defaults to greater when no prefix and no keyword."""
        strike_type, floor, cap = resolve_strike_type_from_prefix("X", None)

        assert strike_type == "greater"


class TestExtractBetweenBounds:
    """Tests for extract_between_bounds function."""

    def test_extracts_floor_and_cap(self) -> None:
        """Extracts floor and cap from tokens."""
        tokens = ["KXBTC", "BETWEEN", "50000", "60000"]

        floor, cap = extract_between_bounds(tokens)

        assert floor == 50000.0
        assert cap == 60000.0

    def test_returns_none_when_no_between(self) -> None:
        """Returns None when no BETWEEN token."""
        tokens = ["KXBTC", "50000"]

        floor, cap = extract_between_bounds(tokens)

        assert floor is None
        assert cap is None

    def test_handles_missing_cap(self) -> None:
        """Handles missing cap token."""
        tokens = ["KXBTC", "BETWEEN", "50000"]

        floor, cap = extract_between_bounds(tokens)

        assert floor == 50000.0
        assert cap is None

    def test_handles_missing_floor_and_cap(self) -> None:
        """Handles missing floor and cap."""
        tokens = ["KXBTC", "BETWEEN"]

        floor, cap = extract_between_bounds(tokens)

        assert floor is None
        assert cap is None

    def test_handles_non_numeric_tokens(self) -> None:
        """Handles non-numeric tokens gracefully."""
        tokens = ["KXBTC", "BETWEEN", "abc", "def"]

        floor, cap = extract_between_bounds(tokens)

        assert floor is None
        assert cap is None

    def test_between_at_end(self) -> None:
        """Handles BETWEEN at end of list."""
        tokens = ["KXBTC", "50000", "BETWEEN"]

        floor, cap = extract_between_bounds(tokens)

        assert floor is None
        assert cap is None


class TestComputeRepresentativeStrike:
    """Tests for compute_representative_strike function."""

    def test_returns_cap_when_available(self) -> None:
        """Returns cap_strike when available."""
        result = compute_representative_strike(60000.0, 50000.0, 55000.0)

        assert result == 60000.0

    def test_returns_floor_when_cap_none(self) -> None:
        """Returns floor_strike when cap is None."""
        result = compute_representative_strike(None, 50000.0, 55000.0)

        assert result == 50000.0

    def test_returns_strike_value_when_both_none(self) -> None:
        """Returns strike_value when both are None."""
        result = compute_representative_strike(None, None, 55000.0)

        assert result == 55000.0

    def test_prefers_cap_over_floor(self) -> None:
        """Prefers cap_strike over floor_strike."""
        result = compute_representative_strike(60000.0, 50000.0, 55000.0)

        assert result == 60000.0
