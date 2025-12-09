"""Unit tests for data_formatting."""

from unittest.mock import Mock

import pytest

from src.common.optimized_status_reporter_helpers.data_formatting import (
    DataFormatting,
)


class TestDataFormatting:
    """Tests for DataFormatting."""

    @pytest.mark.parametrize(
        "value,expected",
        [
            (None, "N/A"),
            (True, "1.0%"),  # bool is subclass of int
            (False, "0.0%"),  # bool is subclass of int
            (100, "100.0%"),
            (75.5, "75.5%"),
            ("50", "50.0%"),
            ("12.345", "12.3%"),  # Rounds to one decimal
            (b"25", "25.0%"),
            (bytearray(b"5.5"), "5.5%"),
            ("abc", "N/A"),
            (b"xyz", "N/A"),
            (bytearray(b"def"), "N/A"),
            ([], "N/A"),
            ({}, "N/A"),
            (Mock(), "N/A"),
        ],
    )
    def test_format_percentage(self, value, expected):
        """Test format_percentage with various inputs."""
        assert DataFormatting.format_percentage(value) == expected
