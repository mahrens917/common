"""Tests for order fills parser."""

from __future__ import annotations

from datetime import datetime

import pytest

from src.common.exceptions import DataError, ValidationError
from src.common.order_response_parser_helpers.order_fills_parser import (
    _extract_fill_count,
    _extract_fill_timestamp,
    _parse_single_fill,
    _validate_fill_fields,
    _validate_total_fill_count,
    parse_fills_from_response,
)


class TestParseFillsFromResponse:
    """Tests for parse_fills_from_response function."""

    def test_returns_empty_list_when_no_fills(self) -> None:
        """Returns empty list when fills data is missing."""
        order_data: dict = {}

        result = parse_fills_from_response(order_data, datetime.now(), 0)

        assert result == []

    def test_returns_empty_list_when_fills_is_none(self) -> None:
        """Returns empty list when fills is None."""
        order_data = {"fills": None}

        result = parse_fills_from_response(order_data, datetime.now(), 0)

        assert result == []

    def test_parses_single_fill(self) -> None:
        """Parses single fill correctly."""
        timestamp = datetime(2025, 1, 15, 12, 0, 0)
        order_data = {"fills": [{"price": 50, "count": 10}]}

        result = parse_fills_from_response(order_data, timestamp, 10)

        assert len(result) == 1
        assert result[0].price_cents == 50
        assert result[0].count == 10

    def test_parses_multiple_fills(self) -> None:
        """Parses multiple fills correctly."""
        timestamp = datetime(2025, 1, 15, 12, 0, 0)
        order_data = {
            "fills": [
                {"price": 45, "count": 5},
                {"price": 55, "count": 7},
            ]
        }

        result = parse_fills_from_response(order_data, timestamp, 12)

        assert len(result) == 2
        assert result[0].count == 5
        assert result[1].count == 7

    def test_raises_when_fill_count_mismatch(self) -> None:
        """Raises ValueError when total fills don't match expected count."""
        order_data = {"fills": [{"price": 50, "count": 5}]}

        with pytest.raises(ValueError, match="Fills count mismatch"):
            parse_fills_from_response(order_data, datetime.now(), 10)


class TestValidateFillFields:
    """Tests for _validate_fill_fields function."""

    def test_passes_when_both_fields_present(self) -> None:
        """Passes validation when price and count present."""
        fill_data = {"price": 50, "count": 5}

        _validate_fill_fields(fill_data)  # Should not raise

    def test_raises_when_price_missing(self) -> None:
        """Raises DataError when price field is missing."""
        fill_data = {"count": 5}

        with pytest.raises(DataError, match="price"):
            _validate_fill_fields(fill_data)

    def test_raises_when_count_missing(self) -> None:
        """Raises DataError when count field is missing."""
        fill_data = {"price": 50}

        with pytest.raises(DataError, match="count"):
            _validate_fill_fields(fill_data)


class TestExtractFillCount:
    """Tests for _extract_fill_count function."""

    def test_extracts_integer_count(self) -> None:
        """Extracts integer count directly."""
        fill_data = {"count": 10}

        result = _extract_fill_count(fill_data)

        assert result == 10

    def test_converts_string_count_to_int(self) -> None:
        """Converts string count to integer."""
        fill_data = {"count": "15"}

        result = _extract_fill_count(fill_data)

        assert result == 15

    def test_converts_float_count_to_int(self) -> None:
        """Converts float count to integer."""
        fill_data = {"count": 20.0}

        result = _extract_fill_count(fill_data)

        assert result == 20

    def test_raises_for_invalid_count(self) -> None:
        """Raises ValidationError for non-numeric count."""
        fill_data = {"count": "invalid"}

        with pytest.raises(ValidationError, match="Invalid fill count"):
            _extract_fill_count(fill_data)

    def test_raises_for_none_count(self) -> None:
        """Raises ValidationError for None count."""
        fill_data = {"count": None}

        with pytest.raises(ValidationError, match="Invalid fill count"):
            _extract_fill_count(fill_data)


class TestExtractFillTimestamp:
    """Tests for _extract_fill_timestamp function."""

    def test_uses_default_when_timestamp_missing(self) -> None:
        """Uses default timestamp when not in fill data."""
        default_ts = datetime(2025, 1, 15, 12, 0, 0)
        fill_data: dict = {}

        result = _extract_fill_timestamp(fill_data, default_ts)

        assert result == default_ts

    def test_parses_iso_timestamp(self) -> None:
        """Parses ISO format timestamp."""
        fill_data = {"timestamp": "2025-01-15T14:30:00+00:00"}
        default_ts = datetime(2025, 1, 1, 0, 0, 0)

        result = _extract_fill_timestamp(fill_data, default_ts)

        assert result.hour == 14
        assert result.minute == 30

    def test_parses_utc_z_timestamp(self) -> None:
        """Parses timestamp with Z suffix."""
        fill_data = {"timestamp": "2025-01-15T16:45:00Z"}
        default_ts = datetime(2025, 1, 1, 0, 0, 0)

        result = _extract_fill_timestamp(fill_data, default_ts)

        assert result.hour == 16
        assert result.minute == 45

    def test_raises_for_invalid_timestamp_format(self) -> None:
        """Raises ValidationError for invalid timestamp format."""
        fill_data = {"timestamp": "not-a-timestamp"}
        default_ts = datetime(2025, 1, 1, 0, 0, 0)

        with pytest.raises(ValidationError, match="Invalid fill timestamp"):
            _extract_fill_timestamp(fill_data, default_ts)


class TestParseSingleFill:
    """Tests for _parse_single_fill function."""

    def test_parses_complete_fill(self) -> None:
        """Parses fill with all fields."""
        fill_data = {
            "price": 65,
            "count": 8,
            "timestamp": "2025-01-15T10:00:00Z",
        }
        default_ts = datetime(2025, 1, 1, 0, 0, 0)

        result = _parse_single_fill(fill_data, default_ts)

        assert result.price_cents == 65
        assert result.count == 8
        assert result.timestamp.hour == 10


class TestValidateTotalFillCount:
    """Tests for _validate_total_fill_count function."""

    def test_passes_when_counts_match(self) -> None:
        """Passes when fill counts sum to expected."""
        from src.common.data_models.trading import OrderFill

        fills = [
            OrderFill(price_cents=50, count=5, timestamp=datetime.now()),
            OrderFill(price_cents=60, count=3, timestamp=datetime.now()),
        ]

        _validate_total_fill_count(fills, 8)  # Should not raise

    def test_raises_when_counts_mismatch(self) -> None:
        """Raises ValueError when counts don't match."""
        from src.common.data_models.trading import OrderFill

        fills = [
            OrderFill(price_cents=50, count=5, timestamp=datetime.now()),
        ]

        with pytest.raises(ValueError, match="Fills count mismatch"):
            _validate_total_fill_count(fills, 10)
