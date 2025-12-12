"""Tests for strike_helpers module."""

import pytest

from common.strike_helpers import (
    calculate_strike_bounds,
    check_strike_in_range,
    compute_strike_value,
    extract_strike_parameters,
    resolve_strike_from_metadata,
)


class TestCalculateStrikeBounds:
    """Tests for calculate_strike_bounds function."""

    def test_greater_type_returns_floor_and_inf(self) -> None:
        """Greater type returns floor strike and infinity cap."""
        strike_type, floor, cap = calculate_strike_bounds("greater", 50000.0)

        assert strike_type == "greater"
        assert floor == 50000.0
        assert cap == float("inf")

    def test_less_type_returns_zero_and_cap(self) -> None:
        """Less type returns zero floor and cap strike."""
        strike_type, floor, cap = calculate_strike_bounds("less", 60000.0)

        assert strike_type == "less"
        assert floor == 0.0
        assert cap == 60000.0

    def test_between_type_returns_margin_bounds(self) -> None:
        """Between type returns bounds with 10% margin."""
        strike_type, floor, cap = calculate_strike_bounds("between", 50000.0)

        assert strike_type == "between"
        assert floor == 45000.0
        assert cap == 55000.0

    def test_unknown_type_defaults_to_greater(self) -> None:
        """Unknown type defaults to greater."""
        strike_type, floor, cap = calculate_strike_bounds("unknown", 50000.0)

        assert strike_type == "greater"
        assert floor == 50000.0
        assert cap == float("inf")


class TestResolveStrikeFromMetadata:
    """Tests for resolve_strike_from_metadata function."""

    def test_returns_none_when_strike_type_missing(self) -> None:
        """Returns None when strike_type is missing."""
        metadata = {"floor_strike": 50000.0, "cap_strike": 60000.0}

        result = resolve_strike_from_metadata(metadata)

        assert result is None

    def test_handles_bytes_strike_type(self) -> None:
        """Handles bytes strike_type."""
        metadata = {"strike_type": b"greater", "floor_strike": 50000.0}

        result = resolve_strike_from_metadata(metadata)

        assert result == 50000.0

    def test_returns_none_on_decode_error(self) -> None:
        """Returns None on decode error."""
        metadata = {"strike_type": b"\xff\xfe", "floor_strike": 50000.0}

        result = resolve_strike_from_metadata(metadata)

        assert result is None


class TestCheckStrikeInRange:
    """Tests for check_strike_in_range function."""

    def test_less_than_format_in_range(self) -> None:
        """Less-than format within range."""
        result = check_strike_in_range("<60000", 50000.0, 70000.0)

        assert result is True

    def test_less_than_format_below_range(self) -> None:
        """Less-than format below range."""
        result = check_strike_in_range("<40000", 50000.0, 70000.0)

        assert result is False

    def test_less_than_format_at_lower_bound(self) -> None:
        """Less-than format at lower bound."""
        result = check_strike_in_range("<50000", 50000.0, 70000.0)

        assert result is True


class TestExtractStrikeParameters:
    """Tests for extract_strike_parameters function."""

    def test_greater_market_with_floor_strike(self) -> None:
        """Greater market with floor strike."""
        market_data = {"floor_strike": 50000.0}

        strike_type, floor, cap = extract_strike_parameters(market_data, "greater")

        assert strike_type == "greater"
        assert floor == 50000.0
        assert cap == float("inf")

    def test_greater_market_missing_floor_raises(self) -> None:
        """Greater market missing floor strike raises."""
        market_data = {}

        with pytest.raises(ValueError, match="Greater market missing required floor_strike"):
            extract_strike_parameters(market_data, "greater")

    def test_less_market_with_cap_strike(self) -> None:
        """Less market with cap strike."""
        market_data = {"cap_strike": 60000.0}

        strike_type, floor, cap = extract_strike_parameters(market_data, "less")

        assert strike_type == "less"
        assert floor == 0.0
        assert cap == 60000.0

    def test_less_market_missing_cap_raises(self) -> None:
        """Less market missing cap strike raises."""
        market_data = {}

        with pytest.raises(ValueError, match="Less market missing required cap_strike"):
            extract_strike_parameters(market_data, "less")

    def test_between_market_with_bounds(self) -> None:
        """Between market with floor and cap strikes."""
        market_data = {"floor_strike": 50000.0, "cap_strike": 60000.0}

        strike_type, floor, cap = extract_strike_parameters(market_data, "between")

        assert strike_type == "between"
        assert floor == 50000.0
        assert cap == 60000.0

    def test_between_market_missing_floor_raises(self) -> None:
        """Between market missing floor strike raises."""
        market_data = {"cap_strike": 60000.0}

        with pytest.raises(ValueError, match="Between market missing required floor_strike or cap_strike"):
            extract_strike_parameters(market_data, "between")

    def test_between_market_missing_cap_raises(self) -> None:
        """Between market missing cap strike raises."""
        market_data = {"floor_strike": 50000.0}

        with pytest.raises(ValueError, match="Between market missing required floor_strike or cap_strike"):
            extract_strike_parameters(market_data, "between")

    def test_unknown_strike_type_raises(self) -> None:
        """Unknown strike type raises."""
        market_data = {"floor_strike": 50000.0}

        with pytest.raises(ValueError, match="Unknown strike_type 'unknown'"):
            extract_strike_parameters(market_data, "unknown")


class TestComputeStrikeValue:
    """Tests for compute_strike_value function."""

    def test_unknown_strike_type(self) -> None:
        """Unknown strike type returns invalid."""
        metadata = {"floor_strike": 50000.0}

        is_valid, reason, strike, floor, cap = compute_strike_value("unknown", metadata)

        assert is_valid is False
        assert reason == "unknown_strike_type"
        assert strike is None

    def test_less_missing_cap(self) -> None:
        """Less type missing cap returns invalid."""
        metadata = {"floor_strike": 50000.0}

        is_valid, reason, strike, floor, cap = compute_strike_value("less", metadata)

        assert is_valid is False
        assert reason == "less_missing_cap"
        assert strike is None

    def test_less_with_cap(self) -> None:
        """Less type with cap returns valid."""
        metadata = {"cap_strike": 60000.0}

        is_valid, reason, strike, floor, cap = compute_strike_value("less", metadata)

        assert is_valid is True
        assert reason is None
        assert strike == 60000.0
        assert cap == 60000.0
