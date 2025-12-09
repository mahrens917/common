"""Tests for common expiry_utils_helpers module."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from src.common.exceptions import DataError
from src.common.expiry_utils_helpers import (
    extract_expiry_from_market,
    parse_expiry_to_datetime,
)
from src.common.expiry_utils_helpers.expiry_extractor import extract_expiry_from_market


class TestExpiryUtilsHelpersModule:
    """Tests for the expiry_utils_helpers module exports."""

    def test_module_exports_extract_expiry_from_market(self) -> None:
        """Module exports extract_expiry_from_market function."""
        from src.common import expiry_utils_helpers

        assert "extract_expiry_from_market" in expiry_utils_helpers.__all__

    def test_module_exports_parse_expiry_to_datetime(self) -> None:
        """Module exports parse_expiry_to_datetime function."""
        from src.common import expiry_utils_helpers

        assert "parse_expiry_to_datetime" in expiry_utils_helpers.__all__


class TestExtractExpiryFromMarket:
    """Tests for extract_expiry_from_market function."""

    def test_extracts_expiry_from_object_with_expiry_time(self) -> None:
        """Extracts expiry from object with expiry_time attribute."""
        market = SimpleNamespace(expiry_time="2024-01-01T12:00:00Z")
        result = extract_expiry_from_market(market)
        assert result == "2024-01-01T12:00:00Z"

    def test_extracts_expiry_from_dict_with_close_time(self) -> None:
        """Extracts expiry from dict with close_time field."""
        market = {"close_time": "2024-01-01T12:00:00Z"}
        result = extract_expiry_from_market(market)
        assert result == "2024-01-01T12:00:00Z"

    def test_extracts_expiry_from_dict_with_expiry(self) -> None:
        """Extracts expiry from dict with expiry field."""
        market = {"expiry": "2024-01-01T12:00:00Z"}
        result = extract_expiry_from_market(market)
        assert result == "2024-01-01T12:00:00Z"

    def test_extracts_expiry_from_dict_with_expiration_time(self) -> None:
        """Extracts expiry from dict with expiration_time field."""
        market = {"expiration_time": "2024-01-01T12:00:00Z"}
        result = extract_expiry_from_market(market)
        assert result == "2024-01-01T12:00:00Z"

    def test_close_time_takes_precedence(self) -> None:
        """close_time takes precedence over other fields."""
        market = {
            "close_time": "2024-01-01T12:00:00Z",
            "expiry": "2024-02-01T12:00:00Z",
        }
        result = extract_expiry_from_market(market)
        assert result == "2024-01-01T12:00:00Z"

    def test_raises_on_empty_dict(self) -> None:
        """Raises DataError for empty dict."""
        with pytest.raises(DataError):
            extract_expiry_from_market({})

    def test_raises_on_dict_without_expiry_fields(self) -> None:
        """Raises DataError for dict without any expiry fields."""
        with pytest.raises(DataError):
            extract_expiry_from_market({"ticker": "TEST"})

    def test_object_takes_precedence_over_dict_fallback(self) -> None:
        """Object with expiry_time is checked before dict-style lookup."""
        market = SimpleNamespace(expiry_time="2024-01-01T12:00:00Z")
        result = extract_expiry_from_market(market)
        assert result == "2024-01-01T12:00:00Z"


class TestParseExpiryToDatetime:
    """Tests for parse_expiry_to_datetime function."""

    def test_parses_iso_string_to_datetime(self) -> None:
        """Parses ISO 8601 string to datetime."""
        result = parse_expiry_to_datetime("2024-01-01T12:00:00Z")
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1

    def test_returns_datetime_unchanged(self) -> None:
        """Returns datetime object unchanged if already datetime."""
        dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = parse_expiry_to_datetime(dt)
        assert result == dt
