"""Tests for kalshi_api response_field_parser."""

from datetime import datetime
from unittest.mock import patch

import pytest

from common.kalshi_api.client_helpers.errors import KalshiClientError
from common.kalshi_api.response_field_parser import ResponseFieldParser


def test_parse_timestamp_delegates():
    with patch("common.kalshi_api.response_field_parser.parse_timestamp") as mock_parse:
        mock_parse.return_value = datetime(2024, 1, 1)
        result = ResponseFieldParser.parse_timestamp("2024-01-01T00:00:00Z")
        mock_parse.assert_called_once_with("2024-01-01T00:00:00Z")
        assert result == datetime(2024, 1, 1)


def test_parse_order_fill_success():
    payload = {
        "price": 50,
        "count": 10,
        "timestamp": "2024-01-01T00:00:00Z",
    }

    with patch("common.kalshi_api.response_field_parser.parse_timestamp") as mock_parse:
        mock_parse.return_value = datetime(2024, 1, 1)
        fill = ResponseFieldParser.parse_order_fill(payload)

    assert fill.price_cents == 50
    assert fill.count == 10


def test_parse_order_fill_missing_price():
    payload = {"count": 10, "timestamp": "2024-01-01T00:00:00Z"}

    with pytest.raises(KalshiClientError) as exc_info:
        ResponseFieldParser.parse_order_fill(payload)

    assert "missing 'price'" in str(exc_info.value)


def test_parse_order_fill_missing_count():
    payload = {"price": 50, "timestamp": "2024-01-01T00:00:00Z"}

    with pytest.raises(KalshiClientError) as exc_info:
        ResponseFieldParser.parse_order_fill(payload)

    assert "missing 'count'" in str(exc_info.value)


def test_parse_order_fill_missing_timestamp():
    payload = {"price": 50, "count": 10}

    with pytest.raises(KalshiClientError) as exc_info:
        ResponseFieldParser.parse_order_fill(payload)

    assert "missing 'timestamp'" in str(exc_info.value)


def test_parse_order_fill_invalid_values():
    payload = {"price": "not_a_number", "count": 10, "timestamp": "2024-01-01T00:00:00Z"}

    with pytest.raises(KalshiClientError) as exc_info:
        ResponseFieldParser.parse_order_fill(payload)

    assert "Invalid fill payload" in str(exc_info.value)


def test_normalise_fill_success():
    payload = {"fill_id": "123", "timestamp": "2024-01-01T00:00:00Z"}

    with patch("common.kalshi_api.response_field_parser.parse_timestamp") as mock_parse:
        mock_parse.return_value = datetime(2024, 1, 1)
        result = ResponseFieldParser.normalise_fill(payload)

    assert result["fill_id"] == "123"
    assert result["timestamp"] == datetime(2024, 1, 1)


def test_normalise_fill_missing_timestamp():
    payload = {"fill_id": "123"}

    with pytest.raises(KalshiClientError) as exc_info:
        ResponseFieldParser.normalise_fill(payload)

    assert "missing timestamp" in str(exc_info.value)


def test_normalise_fill_invalid_timestamp():
    payload = {"fill_id": "123", "timestamp": "invalid"}

    with patch("common.kalshi_api.response_field_parser.parse_timestamp") as mock_parse:
        mock_parse.side_effect = ValueError("bad timestamp")

        with pytest.raises(KalshiClientError) as exc_info:
            ResponseFieldParser.normalise_fill(payload)

        assert "Invalid fill timestamp" in str(exc_info.value)


def test_normalise_fill_none_timestamp():
    payload = {"fill_id": "123", "timestamp": "2024-01-01"}

    with patch("common.kalshi_api.response_field_parser.parse_timestamp") as mock_parse:
        mock_parse.return_value = None

        with pytest.raises(KalshiClientError) as exc_info:
            ResponseFieldParser.normalise_fill(payload)

        assert "Invalid fill timestamp" in str(exc_info.value)


def test_extract_raw_values_success():
    payload = {
        "order_id": "order-123",
        "client_order_id": "client-456",
        "status": "filled",
        "filled_count": 10,
        "remaining_count": 0,
        "fees": 5,
        "timestamp": "2024-01-01T00:00:00Z",
        "fills": [],
    }

    result = ResponseFieldParser.extract_raw_values(payload)

    assert result["order_id"] == "order-123"
    assert result["client_order_id"] == "client-456"
    assert result["status_raw"] == "filled"
    assert result["filled_count"] == 10
    assert result["remaining_count"] == 0
    assert result["fees_cents"] == 5


def test_extract_raw_values_empty_order_id():
    payload = {
        "order_id": "  ",
        "client_order_id": "client-456",
        "status": "filled",
        "filled_count": 10,
        "remaining_count": 0,
        "fees": 5,
        "timestamp": "2024-01-01T00:00:00Z",
        "fills": [],
    }

    with pytest.raises(KalshiClientError) as exc_info:
        ResponseFieldParser.extract_raw_values(payload)

    assert "missing identifier data" in str(exc_info.value)


def test_extract_raw_values_invalid_int():
    payload = {
        "order_id": "order-123",
        "client_order_id": "client-456",
        "status": "filled",
        "filled_count": "not_a_number",
        "remaining_count": 0,
        "fees": 5,
        "timestamp": "2024-01-01T00:00:00Z",
        "fills": [],
    }

    with pytest.raises(KalshiClientError) as exc_info:
        ResponseFieldParser.extract_raw_values(payload)

    assert "Invalid order payload" in str(exc_info.value)


def test_parse_average_fill_price_success():
    result = ResponseFieldParser.parse_average_fill_price({"average_fill_price": 50})
    assert result == 50


def test_parse_average_fill_price_none():
    result = ResponseFieldParser.parse_average_fill_price({})
    assert result is None


def test_parse_average_fill_price_invalid():
    with pytest.raises(KalshiClientError) as exc_info:
        ResponseFieldParser.parse_average_fill_price({"average_fill_price": "not_a_number"})

    assert "Invalid average fill price" in str(exc_info.value)


def test_parse_fills_list_empty():
    result = ResponseFieldParser.parse_fills_list([])
    assert result == []


def test_parse_fills_list_not_list():
    with pytest.raises(KalshiClientError) as exc_info:
        ResponseFieldParser.parse_fills_list("not a list")

    assert "must be a list" in str(exc_info.value)


def test_parse_fills_list_item_not_dict():
    with pytest.raises(KalshiClientError) as exc_info:
        ResponseFieldParser.parse_fills_list(["not a dict"])

    assert "must be a JSON object" in str(exc_info.value)


def test_extract_ticker_success():
    result = ResponseFieldParser.extract_ticker({"ticker": "  ABC-DEF  "})
    assert result == "ABC-DEF"


def test_extract_ticker_empty():
    with pytest.raises(KalshiClientError) as exc_info:
        ResponseFieldParser.extract_ticker({"ticker": "   "})

    assert "missing ticker" in str(exc_info.value)
