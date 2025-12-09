"""Tests for level processor module."""

from unittest.mock import patch

import pytest

from src.common.exceptions import DataError
from src.common.redis_protocol.orderbook_utils_helpers.level_processor import (
    LevelProcessor,
)


class TestLevelProcessorValidatePriceLevel:
    """Tests for LevelProcessor.validate_price_level."""

    def test_valid_list_level(self) -> None:
        """Accepts valid list price level."""
        result = LevelProcessor.validate_price_level([50, 100], "KXBTC-25JAN01")

        assert result is True

    def test_valid_tuple_level(self) -> None:
        """Accepts valid tuple price level."""
        result = LevelProcessor.validate_price_level((50, 100), "KXBTC-25JAN01")

        assert result is True

    def test_invalid_single_element(self) -> None:
        """Raises DataError for single element."""
        with pytest.raises(DataError) as exc_info:
            LevelProcessor.validate_price_level([50], "KXBTC-25JAN01")

        assert "Corrupted order book data" in str(exc_info.value)

    def test_invalid_non_sequence(self) -> None:
        """Raises DataError for non-sequence."""
        with pytest.raises(DataError) as exc_info:
            LevelProcessor.validate_price_level(50, "KXBTC-25JAN01")

        assert "Corrupted order book data" in str(exc_info.value)


class TestLevelProcessorIsValidSize:
    """Tests for LevelProcessor.is_valid_size."""

    def test_valid_int(self) -> None:
        """Returns True for positive int."""
        assert LevelProcessor.is_valid_size(100) is True

    def test_valid_float(self) -> None:
        """Returns True for positive float."""
        assert LevelProcessor.is_valid_size(100.5) is True

    def test_zero_invalid(self) -> None:
        """Returns False for zero."""
        assert LevelProcessor.is_valid_size(0) is False

    def test_negative_invalid(self) -> None:
        """Returns False for negative."""
        assert LevelProcessor.is_valid_size(-10) is False

    def test_string_invalid(self) -> None:
        """Returns False for string."""
        assert LevelProcessor.is_valid_size("100") is False

    def test_none_invalid(self) -> None:
        """Returns False for None."""
        assert LevelProcessor.is_valid_size(None) is False


class TestLevelProcessorProcessYesLevel:
    """Tests for LevelProcessor.process_yes_level."""

    def test_adds_to_yes_bids(self) -> None:
        """Adds price level to yes_bids."""
        orderbook_sides = {"yes_bids": {}, "yes_asks": {}}

        LevelProcessor.process_yes_level(50, 100, orderbook_sides)

        assert orderbook_sides["yes_bids"]["50"] == 100


class TestLevelProcessorProcessNoLevel:
    """Tests for LevelProcessor.process_no_level."""

    def test_converts_and_adds_to_yes_asks(self) -> None:
        """Converts NO price and adds to yes_asks."""
        orderbook_sides = {"yes_bids": {}, "yes_asks": {}}

        LevelProcessor.process_no_level(40, 100, orderbook_sides)

        assert orderbook_sides["yes_asks"]["60.0"] == 100


class TestLevelProcessorProcessSideLevels:
    """Tests for LevelProcessor.process_side_levels."""

    def test_process_yes_side(self) -> None:
        """Processes YES side levels."""
        orderbook_sides = {"yes_bids": {}, "yes_asks": {}}
        levels = [[50, 100], [55, 200]]

        LevelProcessor.process_side_levels("yes", levels, "KXBTC-25JAN01", orderbook_sides)

        assert orderbook_sides["yes_bids"] == {"50": 100, "55": 200}

    def test_process_no_side(self) -> None:
        """Processes NO side levels."""
        orderbook_sides = {"yes_bids": {}, "yes_asks": {}}
        levels = [[40, 100], [30, 200]]

        LevelProcessor.process_side_levels("no", levels, "KXBTC-25JAN01", orderbook_sides)

        assert orderbook_sides["yes_asks"] == {"60.0": 100, "70.0": 200}

    def test_skips_invalid_size(self) -> None:
        """Skips levels with invalid size."""
        orderbook_sides = {"yes_bids": {}, "yes_asks": {}}
        levels = [[50, 0], [55, 100]]

        LevelProcessor.process_side_levels("yes", levels, "KXBTC-25JAN01", orderbook_sides)

        assert orderbook_sides["yes_bids"] == {"55": 100}

    def test_raises_on_invalid_level_structure(self) -> None:
        """Raises DataError for invalid level structure."""
        orderbook_sides = {"yes_bids": {}, "yes_asks": {}}
        levels = [[50]]

        with pytest.raises(DataError):
            LevelProcessor.process_side_levels("yes", levels, "KXBTC-25JAN01", orderbook_sides)
