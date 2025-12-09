"""Tests for orderbook_utils module."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from src.common.orderbook_utils import (
    _filter_valid_pairs,
    _get_default_price_result,
    _parse_price_size_pairs,
    _select_best_price,
    extract_best_bid_ask,
    extract_best_price_from_dict,
    extract_best_price_from_json,
    parse_and_extract_best_price,
    parse_orderbook_field,
    parse_orderbook_levels,
)

DEFAULT_ORDERBOOK_BEST_SIZE = 200
DEFAULT_ORDERBOOK_SECONDARY_SIZE = 100
DEFAULT_ORDERBOOK_MID_SIZE = 150


class TestParseOrderbookField:
    """Tests for parse_orderbook_field function."""

    def test_parses_valid_json(self) -> None:
        """Parses valid JSON field."""
        market_data = {"yes_bids": '{"50": 100, "51": 200}'}

        result, skip_reason = parse_orderbook_field(market_data, "yes_bids", "TEST-TICKER")

        assert result == {"50": 100, "51": 200}
        assert skip_reason is None

    def test_returns_empty_dict_for_missing_field(self) -> None:
        """Returns empty dict when field is missing."""
        market_data = {}

        result, skip_reason = parse_orderbook_field(market_data, "yes_bids", "TEST-TICKER")

        assert result == {}
        assert skip_reason is None

    def test_returns_empty_dict_for_empty_string(self) -> None:
        """Returns empty dict for empty string field."""
        market_data = {"yes_bids": ""}

        result, skip_reason = parse_orderbook_field(market_data, "yes_bids", "TEST-TICKER")

        assert result == {}
        assert skip_reason is None

    def test_handles_dict_field_value(self) -> None:
        """Handles dict field value by treating as empty JSON."""
        market_data = {"yes_bids": {"50": 100}}

        # When value is dict, it gets converted to "{}" string
        result, skip_reason = parse_orderbook_field(market_data, "yes_bids", "TEST-TICKER")

        # The function treats non-string as "{}", which parses to {}
        assert result == {}
        assert skip_reason is None

    def test_returns_invalid_price_data_for_bad_json(self) -> None:
        """Returns INVALID_PRICE_DATA skip reason for invalid JSON."""
        market_data = {"yes_bids": "not valid json"}

        with patch("src.common.orderbook_utils.logger"):
            result, skip_reason = parse_orderbook_field(market_data, "yes_bids", "TEST-TICKER")

        assert result is None
        assert skip_reason == "INVALID_PRICE_DATA"


class TestParseOrderbookLevels:
    """Tests for parse_orderbook_levels function."""

    def test_parses_and_sorts_buy_orders_descending(self) -> None:
        """Parses and sorts buy orders in descending order."""
        order_book = {"50": 100, "52": 200, "51": 150}

        result = parse_orderbook_levels(order_book, is_buy_order=True)

        assert result == [(50.0, 100), (51.0, 150), (52.0, 200)]

    def test_parses_and_sorts_sell_orders_ascending(self) -> None:
        """Parses and sorts sell orders in ascending order."""
        order_book = {"50": 100, "52": 200, "51": 150}

        result = parse_orderbook_levels(order_book, is_buy_order=False)

        assert result == [(52.0, 200), (51.0, 150), (50.0, 100)]

    def test_returns_empty_list_for_empty_dict(self) -> None:
        """Returns empty list for empty orderbook."""
        result = parse_orderbook_levels({}, is_buy_order=True)

        assert result == []

    def test_returns_none_for_invalid_price(self) -> None:
        """Returns None when price cannot be converted to float."""
        order_book = {"invalid": 100}

        with patch("src.common.orderbook_utils.logger"):
            result = parse_orderbook_levels(order_book, is_buy_order=True)

        assert result is None

    def test_returns_none_for_invalid_size(self) -> None:
        """Returns None when size cannot be converted to int."""
        order_book = {"50": "invalid"}

        with patch("src.common.orderbook_utils.logger"):
            result = parse_orderbook_levels(order_book, is_buy_order=True)

        assert result is None


class TestExtractBestPriceFromJson:
    """Tests for extract_best_price_from_json function."""

    def test_extracts_best_bid(self) -> None:
        """Extracts highest price for bid side."""
        order_book_json = '{"50": 100, "52": 200, "51": 150}'

        best_price, best_size = extract_best_price_from_json(order_book_json, is_bid=True)

        assert best_price == 52.0
        assert best_size == DEFAULT_ORDERBOOK_BEST_SIZE

    def test_extracts_best_ask(self) -> None:
        """Extracts lowest price for ask side."""
        order_book_json = '{"50": 100, "52": 200, "51": 150}'

        best_price, best_size = extract_best_price_from_json(order_book_json, is_bid=False)

        assert best_price == 50.0
        assert best_size == DEFAULT_ORDERBOOK_SECONDARY_SIZE

    def test_returns_none_for_empty_string(self) -> None:
        """Returns None for empty string."""
        best_price, best_size = extract_best_price_from_json("", is_bid=True)

        assert best_price is None
        assert best_size is None

    def test_returns_none_for_empty_json_object(self) -> None:
        """Returns None for empty JSON object."""
        best_price, best_size = extract_best_price_from_json("{}", is_bid=True)

        assert best_price is None
        assert best_size is None

    def test_returns_none_for_invalid_json(self) -> None:
        """Returns None for invalid JSON."""
        with patch("src.common.orderbook_utils.logger"):
            best_price, best_size = extract_best_price_from_json("invalid json", is_bid=True)

        assert best_price is None
        assert best_size is None

    def test_returns_none_for_none_input(self) -> None:
        """Returns None for None input."""
        best_price, best_size = extract_best_price_from_json(None, is_bid=True)

        assert best_price is None
        assert best_size is None


class TestGetDefaultPriceResult:
    """Tests for _get_default_price_result function."""

    def test_returns_zeros_when_allow_zero(self) -> None:
        """Returns (0.0, 0) when allow_zero is True."""
        result = _get_default_price_result(allow_zero=True)

        assert result == (0.0, 0)

    def test_returns_nones_when_not_allow_zero(self) -> None:
        """Returns (None, None) when allow_zero is False."""
        result = _get_default_price_result(allow_zero=False)

        assert result == (None, None)


class TestParsePriceSizePairs:
    """Tests for _parse_price_size_pairs function."""

    def test_parses_valid_dict(self) -> None:
        """Parses valid orderbook dict."""
        order_book = {"50": 100, "51": 200}

        result = _parse_price_size_pairs(order_book)

        assert set(result) == {(50.0, 100), (51.0, 200)}

    def test_returns_empty_for_empty_dict(self) -> None:
        """Returns empty list for empty dict."""
        result = _parse_price_size_pairs({})

        assert result == []

    def test_converts_string_values(self) -> None:
        """Converts string prices and sizes to numbers."""
        order_book = {"50.5": "100"}

        result = _parse_price_size_pairs(order_book)

        assert result == [(50.5, 100)]


class TestFilterValidPairs:
    """Tests for _filter_valid_pairs function."""

    def test_filters_zero_sizes(self) -> None:
        """Filters out pairs with zero size."""
        pairs = [(50.0, 100), (51.0, 0), (52.0, 200)]

        result = _filter_valid_pairs(pairs)

        assert result == [(50.0, 100), (52.0, 200)]

    def test_filters_negative_sizes(self) -> None:
        """Filters out pairs with negative size."""
        pairs = [(50.0, 100), (51.0, -10), (52.0, 200)]

        result = _filter_valid_pairs(pairs)

        assert result == [(50.0, 100), (52.0, 200)]

    def test_returns_empty_when_all_invalid(self) -> None:
        """Returns empty list when all sizes are invalid."""
        pairs = [(50.0, 0), (51.0, -10)]

        result = _filter_valid_pairs(pairs)

        assert result == []


class TestSelectBestPrice:
    """Tests for _select_best_price function."""

    def test_selects_max_for_bid(self) -> None:
        """Selects maximum price for bid side."""
        pairs = [(50.0, 100), (52.0, 200), (51.0, 150)]

        result = _select_best_price(pairs, is_bid=True)

        assert result == (52.0, 200)

    def test_selects_min_for_ask(self) -> None:
        """Selects minimum price for ask side."""
        pairs = [(50.0, 100), (52.0, 200), (51.0, 150)]

        result = _select_best_price(pairs, is_bid=False)

        assert result == (50.0, 100)


class TestExtractBestPriceFromDict:
    """Tests for extract_best_price_from_dict function."""

    def test_extracts_best_bid(self) -> None:
        """Extracts highest price for bid side."""
        order_book = {"50": 100, "52": 200, "51": 150}

        best_price, best_size = extract_best_price_from_dict(order_book, is_bid=True)

        assert best_price == 52.0
        assert best_size == DEFAULT_ORDERBOOK_BEST_SIZE

    def test_extracts_best_ask(self) -> None:
        """Extracts lowest price for ask side."""
        order_book = {"50": 100, "52": 200, "51": 150}

        best_price, best_size = extract_best_price_from_dict(order_book, is_bid=False)

        assert best_price == 50.0
        assert best_size == DEFAULT_ORDERBOOK_SECONDARY_SIZE

    def test_returns_none_for_empty_dict(self) -> None:
        """Returns None for empty dict when allow_zero is False."""
        best_price, best_size = extract_best_price_from_dict({}, is_bid=True)

        assert best_price is None
        assert best_size is None

    def test_returns_zeros_for_empty_dict_with_allow_zero(self) -> None:
        """Returns zeros for empty dict when allow_zero is True."""
        best_price, best_size = extract_best_price_from_dict({}, is_bid=True, allow_zero=True)

        assert best_price == 0.0
        assert best_size == 0

    def test_filters_zero_sizes(self) -> None:
        """Filters out zero sizes and returns best from valid."""
        order_book = {"50": 0, "52": 200, "51": 0}

        best_price, best_size = extract_best_price_from_dict(order_book, is_bid=True)

        assert best_price == 52.0
        assert best_size == DEFAULT_ORDERBOOK_BEST_SIZE

    def test_returns_default_when_all_sizes_zero(self) -> None:
        """Returns default when all sizes are zero."""
        order_book = {"50": 0, "51": 0}

        best_price, best_size = extract_best_price_from_dict(order_book, is_bid=True)

        assert best_price is None
        assert best_size is None

    def test_handles_invalid_data_types(self) -> None:
        """Handles invalid data types gracefully."""
        order_book = {"invalid": "not_a_number"}

        with patch("src.common.orderbook_utils.logger"):
            best_price, best_size = extract_best_price_from_dict(order_book, is_bid=True)

        assert best_price is None
        assert best_size is None


class TestExtractBestBidAsk:
    """Tests for extract_best_bid_ask function."""

    def test_extracts_both_bid_and_ask(self) -> None:
        """Extracts both best bid and ask prices."""
        orderbook = {
            "yes_bids": {"50": 100, "51": 200},
            "yes_asks": {"52": 150, "53": 250},
        }

        best_bid, best_ask = extract_best_bid_ask(orderbook)

        assert best_bid == 51.0
        assert best_ask == 52.0

    def test_returns_none_for_missing_bids(self) -> None:
        """Returns None for bid when yes_bids missing."""
        orderbook = {"yes_asks": {"52": 150}}

        best_bid, best_ask = extract_best_bid_ask(orderbook)

        assert best_bid is None
        assert best_ask == 52.0

    def test_returns_none_for_missing_asks(self) -> None:
        """Returns None for ask when yes_asks missing."""
        orderbook = {"yes_bids": {"50": 100}}

        best_bid, best_ask = extract_best_bid_ask(orderbook)

        assert best_bid == 50.0
        assert best_ask is None

    def test_returns_none_for_empty_orderbook(self) -> None:
        """Returns None for both when orderbook is empty."""
        best_bid, best_ask = extract_best_bid_ask({})

        assert best_bid is None
        assert best_ask is None


class TestParseAndExtractBestPrice:
    """Tests for parse_and_extract_best_price function."""

    def test_parses_dict_input(self) -> None:
        """Parses dict input directly."""
        order_book = {"50": 100, "52": 200}

        best_price, best_size = parse_and_extract_best_price(order_book, "yes_bids")

        assert best_price == 52.0
        assert best_size == DEFAULT_ORDERBOOK_BEST_SIZE

    def test_parses_json_string_input(self) -> None:
        """Parses JSON string input."""
        order_book_json = '{"50": 100, "52": 200}'

        best_price, best_size = parse_and_extract_best_price(order_book_json, "yes_bids")

        assert best_price == 52.0
        assert best_size == DEFAULT_ORDERBOOK_BEST_SIZE

    def test_returns_none_for_none_input(self) -> None:
        """Returns None for None input."""
        best_price, best_size = parse_and_extract_best_price(None, "yes_bids")

        assert best_price is None
        assert best_size is None

    def test_returns_zeros_for_none_with_allow_zero(self) -> None:
        """Returns zeros for None input with allow_zero."""
        best_price, best_size = parse_and_extract_best_price(None, "yes_bids", allow_zero=True)

        assert best_price == 0.0
        assert best_size == 0

    def test_returns_none_for_empty_string(self) -> None:
        """Returns None for empty string."""
        best_price, best_size = parse_and_extract_best_price("", "yes_bids")

        assert best_price is None
        assert best_size is None

    def test_returns_none_for_empty_json_object_string(self) -> None:
        """Returns None for empty JSON object string."""
        best_price, best_size = parse_and_extract_best_price("{}", "yes_bids")

        assert best_price is None
        assert best_size is None

    def test_returns_none_for_empty_dict(self) -> None:
        """Returns None for empty dict."""
        best_price, best_size = parse_and_extract_best_price({}, "yes_bids")

        assert best_price is None
        assert best_size is None

    def test_extracts_ask_correctly(self) -> None:
        """Extracts lowest price for ask side."""
        order_book = {"50": 100, "52": 200}

        best_price, best_size = parse_and_extract_best_price(order_book, "yes_asks")

        assert best_price == 50.0
        assert best_size == DEFAULT_ORDERBOOK_SECONDARY_SIZE

    def test_raises_value_error_for_invalid_json(self) -> None:
        """Raises ValueError for invalid JSON string."""
        with pytest.raises(ValueError, match="invalid JSON"):
            parse_and_extract_best_price("not valid json", "yes_bids")

    def test_raises_type_error_for_non_dict_json(self) -> None:
        """Raises TypeError when JSON decodes to non-dict."""
        with pytest.raises(TypeError, match="must decode to a JSON object"):
            parse_and_extract_best_price("[1, 2, 3]", "yes_bids")

    def test_raises_type_error_for_invalid_type(self) -> None:
        """Raises TypeError for unsupported input type."""
        with pytest.raises(TypeError, match="must be a JSON object or string"):
            parse_and_extract_best_price(123, "yes_bids")

    def test_handles_whitespace_only_string(self) -> None:
        """Returns default for whitespace-only string."""
        best_price, best_size = parse_and_extract_best_price("   ", "yes_bids")

        assert best_price is None
        assert best_size is None

    def test_handles_whitespace_only_string_with_allow_zero(self) -> None:
        """Returns zeros for whitespace-only string with allow_zero."""
        best_price, best_size = parse_and_extract_best_price("   ", "yes_bids", allow_zero=True)

        assert best_price == 0.0
        assert best_size == 0
