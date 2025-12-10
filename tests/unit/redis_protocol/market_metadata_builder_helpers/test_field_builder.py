"""Tests for field builder module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from common.redis_protocol.market_metadata_builder_helpers.field_builder import (
    add_descriptor_fields,
    build_event_fields,
    build_numeric_fields,
    build_orderbook_fields,
    build_orderbook_json_fields,
    build_string_fields,
    build_time_fields,
)


class TestBuildTimeFields:
    """Tests for build_time_fields function."""

    def test_raises_when_close_time_missing(self) -> None:
        """Raises ValueError when close_time missing."""
        market_data = {}
        time_field_keys = {}
        normalizer = MagicMock()

        with pytest.raises(ValueError, match="close_time missing"):
            build_time_fields(market_data, time_field_keys, normalizer)

    def test_extracts_close_time(self) -> None:
        """Extracts and normalizes close_time."""
        market_data = {"close_time": "2025-01-15T12:00:00Z"}
        time_field_keys = {}
        normalizer = MagicMock(return_value="2025-01-15T12:00:00Z")

        result = build_time_fields(market_data, time_field_keys, normalizer)

        assert result["close_time"] == "2025-01-15T12:00:00Z"

    def test_extracts_close_time_ts(self) -> None:
        """Extracts close_time_ts when close_time not present."""
        market_data = {"close_time_ts": "2025-01-15T12:00:00Z"}
        time_field_keys = {}
        normalizer = MagicMock(return_value="2025-01-15T12:00:00Z")

        result = build_time_fields(market_data, time_field_keys, normalizer)

        assert result["close_time"] == "2025-01-15T12:00:00Z"

    def test_raises_when_close_time_is_empty(self) -> None:
        """Raises ValueError when close_time is empty string."""
        market_data = {"close_time": ""}
        time_field_keys = {}
        normalizer = MagicMock()

        # Empty string close_time is treated as missing
        with pytest.raises(ValueError, match="close_time missing"):
            build_time_fields(market_data, time_field_keys, normalizer)

    def test_builds_additional_time_fields(self) -> None:
        """Builds additional time fields from mapping."""
        market_data = {
            "close_time": "2025-01-15T12:00:00Z",
            "open_time": "2025-01-14T12:00:00Z",
            "expiration_time": "2025-01-16T12:00:00Z",
        }
        time_field_keys = {
            "open_time": "open_time",
            "expiration_time": "expiration_time",
        }
        normalizer = MagicMock(side_effect=lambda x: x)

        result = build_time_fields(market_data, time_field_keys, normalizer)

        assert result["open_time"] == "2025-01-14T12:00:00Z"
        assert result["expiration_time"] == "2025-01-16T12:00:00Z"

    def test_handles_none_normalizer_result(self) -> None:
        """Handles None result from normalizer."""
        market_data = {"close_time": "2025-01-15T12:00:00Z"}
        time_field_keys = {}
        normalizer = MagicMock(return_value=None)

        result = build_time_fields(market_data, time_field_keys, normalizer)

        assert result["close_time"] == ""


class TestBuildNumericFields:
    """Tests for build_numeric_fields function."""

    def test_extracts_numeric_fields(self) -> None:
        """Extracts and stringifies numeric fields."""
        market_data = {"volume": 1000, "open_interest": 500}
        numeric_fields = {"volume": 0, "open_interest": 0}
        stringify_func = str

        result = build_numeric_fields(market_data, numeric_fields, stringify_func)

        assert result["volume"] == "1000"
        assert result["open_interest"] == "500"

    def test_uses_default_when_missing(self) -> None:
        """Uses default value when field missing."""
        market_data = {}
        numeric_fields = {"volume": 0, "open_interest": 100}
        stringify_func = str

        result = build_numeric_fields(market_data, numeric_fields, stringify_func)

        assert result["volume"] == "0"
        assert result["open_interest"] == "100"

    def test_applies_stringify_func(self) -> None:
        """Applies stringify function to values."""
        market_data = {"value": 123.456}
        numeric_fields = {"value": 0}
        stringify_func = MagicMock(return_value="123.46")

        result = build_numeric_fields(market_data, numeric_fields, stringify_func)

        assert result["value"] == "123.46"
        stringify_func.assert_called_with(123.456)


class TestBuildStringFields:
    """Tests for build_string_fields function."""

    def test_extracts_string_fields(self) -> None:
        """Extracts and stringifies string fields."""
        market_data = {"status": "open", "result": "pending"}
        string_fields = {"status": "", "result": ""}
        stringify_func = str

        result = build_string_fields(market_data, string_fields, stringify_func)

        assert result["status"] == "open"
        assert result["result"] == "pending"

    def test_uses_default_when_missing(self) -> None:
        """Uses default value when field missing."""
        market_data = {}
        string_fields = {"status": "unknown", "result": "N/A"}
        stringify_func = str

        result = build_string_fields(market_data, string_fields, stringify_func)

        assert result["status"] == "unknown"
        assert result["result"] == "N/A"


class TestBuildOrderbookFields:
    """Tests for build_orderbook_fields function."""

    def test_extracts_orderbook_fields(self) -> None:
        """Extracts orderbook fields."""
        market_data = {"yes_bid": 50, "yes_ask": 55, "no_bid": 45}
        orderbook_fields = ["yes_bid", "yes_ask", "no_bid"]
        stringify_func = str

        result = build_orderbook_fields(market_data, orderbook_fields, stringify_func)

        assert result["yes_bid"] == "50"
        assert result["yes_ask"] == "55"
        assert result["no_bid"] == "45"

    def test_handles_none_values(self) -> None:
        """Handles None values from market data."""
        market_data = {"yes_bid": None}
        orderbook_fields = ["yes_bid"]
        stringify_func = lambda x: str(x) if x is not None else ""

        result = build_orderbook_fields(market_data, orderbook_fields, stringify_func)

        assert result["yes_bid"] == ""


class TestBuildOrderbookJsonFields:
    """Tests for build_orderbook_json_fields function."""

    def test_extracts_json_fields(self) -> None:
        """Extracts and JSON stringifies fields."""
        market_data = {
            "yes_sub_title": ["a", "b"],
            "no_sub_title": ["c", "d"],
        }
        json_fields = ["yes_sub_title", "no_sub_title"]
        json_stringify_func = MagicMock(side_effect=lambda x: str(x))

        result = build_orderbook_json_fields(market_data, json_fields, json_stringify_func)

        assert "yes_sub_title" in result
        assert "no_sub_title" in result


class TestBuildEventFields:
    """Tests for build_event_fields function."""

    def test_extracts_all_event_fields(self) -> None:
        """Extracts all event-related fields."""
        event_data = {
            "ticker": "EVENT-123",
            "title": "Test Event",
            "name": "test_event",
            "category": "test",
            "series_ticker": "SERIES-123",
            "strike_date": "2025-01-15",
            "event_type": "binary",
            "sub_title": "Subtitle",
            "strike_period": "daily",
            "mutually_exclusive": True,
            "collateral_return_type": "return_type",
            "description": "Event description",
            "tags": ["tag1", "tag2"],
            "status": "open",
            "created_time": "2025-01-01T00:00:00Z",
            "modified_time": "2025-01-02T00:00:00Z",
        }
        stringify_func = str
        value_or_default_func = lambda data, key, default: data.get(key, default)

        result = build_event_fields(event_data, stringify_func, value_or_default_func)

        assert result["event_ticker"] == "EVENT-123"
        assert result["event_title"] == "Test Event"
        assert result["event_name"] == "test_event"
        assert result["event_category"] == "test"
        assert result["series_ticker"] == "SERIES-123"
        assert result["strike_date"] == "2025-01-15"
        assert result["event_type"] == "binary"
        assert result["event_subtitle"] == "Subtitle"
        assert result["strike_period"] == "daily"
        assert result["mutually_exclusive"] == "true"
        assert result["collateral_return_type"] == "return_type"
        assert result["event_description"] == "Event description"
        assert result["event_status"] == "open"

    def test_handles_missing_fields(self) -> None:
        """Handles missing fields with None values."""
        event_data = {}
        stringify_func = lambda x: str(x) if x is not None else "None"
        value_or_default_func = lambda data, key, default: data.get(key, default)

        result = build_event_fields(event_data, stringify_func, value_or_default_func)

        assert "event_ticker" in result
        assert "event_title" in result

    def test_lowercases_mutually_exclusive(self) -> None:
        """Lowercases mutually_exclusive value."""
        event_data = {"mutually_exclusive": True}
        stringify_func = str
        value_or_default_func = lambda data, key, default: data.get(key, default)

        result = build_event_fields(event_data, stringify_func, value_or_default_func)

        assert result["mutually_exclusive"] == "true"


class TestAddDescriptorFields:
    """Tests for add_descriptor_fields function."""

    def test_adds_ticker_when_missing(self) -> None:
        """Adds ticker field when not in metadata."""
        metadata = {}
        descriptor = MagicMock()
        descriptor.ticker = "TICKER-123"
        descriptor.category.value = "test"
        descriptor.underlying = None
        descriptor.expiry_token = None

        add_descriptor_fields(metadata, descriptor)

        assert metadata["ticker"] == "TICKER-123"

    def test_does_not_overwrite_ticker(self) -> None:
        """Does not overwrite existing ticker."""
        metadata = {"ticker": "EXISTING"}
        descriptor = MagicMock()
        descriptor.ticker = "NEW"
        descriptor.category.value = "test"
        descriptor.underlying = None
        descriptor.expiry_token = None

        add_descriptor_fields(metadata, descriptor)

        assert metadata["ticker"] == "EXISTING"

    def test_adds_category_when_missing(self) -> None:
        """Adds category field when not in metadata."""
        metadata = {}
        descriptor = MagicMock()
        descriptor.ticker = "TICKER"
        descriptor.category.value = "temperature"
        descriptor.underlying = None
        descriptor.expiry_token = None

        add_descriptor_fields(metadata, descriptor)

        assert metadata["category"] == "temperature"

    def test_adds_underlying_when_present(self) -> None:
        """Adds underlying when descriptor has it."""
        metadata = {}
        descriptor = MagicMock()
        descriptor.ticker = "TICKER"
        descriptor.category.value = "test"
        descriptor.underlying = "BTC"
        descriptor.expiry_token = None

        add_descriptor_fields(metadata, descriptor)

        assert metadata["underlying"] == "BTC"

    def test_does_not_overwrite_underlying(self) -> None:
        """Does not overwrite existing underlying."""
        metadata = {"underlying": "ETH"}
        descriptor = MagicMock()
        descriptor.ticker = "TICKER"
        descriptor.category.value = "test"
        descriptor.underlying = "BTC"
        descriptor.expiry_token = None

        add_descriptor_fields(metadata, descriptor)

        assert metadata["underlying"] == "ETH"

    def test_adds_expiry_token_using_setdefault(self) -> None:
        """Adds expiry_token using setdefault."""
        metadata = {}
        descriptor = MagicMock()
        descriptor.ticker = "TICKER"
        descriptor.category.value = "test"
        descriptor.underlying = None
        descriptor.expiry_token = "25JAN15"

        add_descriptor_fields(metadata, descriptor)

        assert metadata["expiry_token"] == "25JAN15"

    def test_does_not_overwrite_expiry_token(self) -> None:
        """Does not overwrite existing expiry_token."""
        metadata = {"expiry_token": "25JAN01"}
        descriptor = MagicMock()
        descriptor.ticker = "TICKER"
        descriptor.category.value = "test"
        descriptor.underlying = None
        descriptor.expiry_token = "25JAN15"

        add_descriptor_fields(metadata, descriptor)

        assert metadata["expiry_token"] == "25JAN01"
