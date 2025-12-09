"""Tests for fill price extractor."""

from __future__ import annotations

from src.common.order_response_parser_helpers.fill_price_extractor import (
    _is_valid_maker_cost,
    extract_average_fill_price,
)

DEFAULT_MAKER_COST = 500
ZERO_MAKER_COST = 0
NEGATIVE_MAKER_COST = -100
FLOAT_MAKER_COST = 550.0
DEFAULT_DIVISOR = 10


class TestExtractAverageFillPrice:
    """Tests for extract_average_fill_price function."""

    def test_returns_none_when_filled_count_zero(self) -> None:
        """Returns None when filled_count is zero."""
        order_data = {"maker_fill_cost": DEFAULT_MAKER_COST}

        result = extract_average_fill_price(order_data, 0)

        assert result is None

    def test_returns_none_when_filled_count_negative(self) -> None:
        """Returns None when filled_count is negative."""
        order_data = {"maker_fill_cost": DEFAULT_MAKER_COST}

        result = extract_average_fill_price(order_data, -1)

        assert result is None

    def test_calculates_average_from_maker_cost(self) -> None:
        """Calculates average price from maker_fill_cost."""
        order_data = {"maker_fill_cost": DEFAULT_MAKER_COST}

        result = extract_average_fill_price(order_data, DEFAULT_DIVISOR)

        assert result == DEFAULT_MAKER_COST // DEFAULT_DIVISOR

    def test_returns_none_when_maker_cost_missing(self) -> None:
        """Returns None when maker_fill_cost is missing."""
        order_data = {}

        result = extract_average_fill_price(order_data, 5)

        assert result is None

    def test_returns_none_when_maker_cost_zero(self) -> None:
        """Returns None when maker_fill_cost is zero."""
        order_data = {"maker_fill_cost": ZERO_MAKER_COST}

        result = extract_average_fill_price(order_data, 5)

        assert result is None

    def test_returns_none_when_maker_cost_negative(self) -> None:
        """Returns None when maker_fill_cost is negative."""
        order_data = {"maker_fill_cost": NEGATIVE_MAKER_COST}

        result = extract_average_fill_price(order_data, 5)

        assert result is None

    def test_handles_float_maker_cost(self) -> None:
        """Handles float maker_fill_cost value."""
        order_data = {"maker_fill_cost": FLOAT_MAKER_COST}

        result = extract_average_fill_price(order_data, DEFAULT_DIVISOR)

        assert result == int(FLOAT_MAKER_COST // DEFAULT_DIVISOR)


class TestIsValidMakerCost:
    """Tests for _is_valid_maker_cost function."""

    def test_returns_true_for_positive_int(self) -> None:
        """Returns True for positive integer."""
        assert _is_valid_maker_cost(100) is True

    def test_returns_true_for_positive_float(self) -> None:
        """Returns True for positive float."""
        assert _is_valid_maker_cost(100.5) is True

    def test_returns_false_for_zero(self) -> None:
        """Returns False for zero."""
        assert _is_valid_maker_cost(0) is False

    def test_returns_false_for_negative(self) -> None:
        """Returns False for negative value."""
        assert _is_valid_maker_cost(-100) is False

    def test_returns_false_for_none(self) -> None:
        """Returns False for None."""
        assert _is_valid_maker_cost(None) is False

    def test_returns_false_for_string(self) -> None:
        """Returns False for string."""
        assert _is_valid_maker_cost("100") is False
