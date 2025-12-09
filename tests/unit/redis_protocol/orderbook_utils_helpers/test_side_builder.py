"""Tests for side builder module."""

from src.common.redis_protocol.orderbook_utils_helpers.side_builder import (
    process_no_levels,
    process_yes_levels,
)


class TestProcessYesLevels:
    """Tests for process_yes_levels function."""

    def test_empty_list_returns_empty_dict(self) -> None:
        """Returns empty dict for empty list."""
        result = process_yes_levels([])

        assert result == {}

    def test_valid_levels(self) -> None:
        """Processes valid price levels."""
        levels = [[50, 100], [55, 200]]

        result = process_yes_levels(levels)

        assert result == {"50": 100, "55": 200}

    def test_valid_tuple_levels(self) -> None:
        """Processes valid tuple levels."""
        levels = [(50, 100), (55, 200)]

        result = process_yes_levels(levels)

        assert result == {"50": 100, "55": 200}

    def test_skips_invalid_level_structure(self) -> None:
        """Skips levels with invalid structure."""
        levels = [[50, 100], [55], [60, 200]]

        result = process_yes_levels(levels)

        assert result == {"50": 100, "60": 200}

    def test_skips_zero_size(self) -> None:
        """Skips levels with zero size."""
        levels = [[50, 0], [55, 100]]

        result = process_yes_levels(levels)

        assert result == {"55": 100}

    def test_skips_negative_size(self) -> None:
        """Skips levels with negative size."""
        levels = [[50, -10], [55, 100]]

        result = process_yes_levels(levels)

        assert result == {"55": 100}

    def test_skips_non_numeric_size(self) -> None:
        """Skips levels with non-numeric size."""
        levels = [[50, "invalid"], [55, 100]]

        result = process_yes_levels(levels)

        assert result == {"55": 100}

    def test_accepts_float_size(self) -> None:
        """Accepts float size values."""
        levels = [[50, 100.5]]

        result = process_yes_levels(levels)

        assert result == {"50": 100.5}


class TestProcessNoLevels:
    """Tests for process_no_levels function."""

    def test_empty_list_returns_empty_dict(self) -> None:
        """Returns empty dict for empty list."""
        result = process_no_levels([])

        assert result == {}

    def test_converts_price(self) -> None:
        """Converts NO price to YES ask price."""
        levels = [[40, 100]]

        result = process_no_levels(levels)

        assert result == {"60.0": 100}

    def test_multiple_levels(self) -> None:
        """Processes multiple price levels."""
        levels = [[40, 100], [30, 200]]

        result = process_no_levels(levels)

        assert result == {"60.0": 100, "70.0": 200}

    def test_skips_invalid_level_structure(self) -> None:
        """Skips levels with invalid structure."""
        levels = [[40, 100], [30], [20, 200]]

        result = process_no_levels(levels)

        assert result == {"60.0": 100, "80.0": 200}

    def test_skips_zero_size(self) -> None:
        """Skips levels with zero size."""
        levels = [[40, 0], [30, 100]]

        result = process_no_levels(levels)

        assert result == {"70.0": 100}

    def test_skips_negative_size(self) -> None:
        """Skips levels with negative size."""
        levels = [[40, -10], [30, 100]]

        result = process_no_levels(levels)

        assert result == {"70.0": 100}
