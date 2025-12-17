"""Tests for kalshi_api response_parser."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from common.kalshi_api.client_helpers.errors import KalshiClientError
from common.kalshi_api.response_parser import ResponseParser


def test_parse_order_fill_delegates():
    with patch("common.kalshi_api.response_parser.ResponseFieldParser") as mock_parser:
        mock_parser.parse_order_fill.return_value = MagicMock()

        result = ResponseParser.parse_order_fill({"fill": "data"})

        mock_parser.parse_order_fill.assert_called_once_with({"fill": "data"})


def test_normalise_fill_delegates():
    with patch("common.kalshi_api.response_parser.ResponseFieldParser") as mock_parser:
        mock_parser.normalise_fill.return_value = {"normalized": True}

        result = ResponseParser.normalise_fill({"raw": "data"})

        mock_parser.normalise_fill.assert_called_once_with({"raw": "data"})
        assert result == {"normalized": True}


def test_parse_enum_fields_success():
    payload = {
        "side": "yes",
        "action": "buy",
        "type": "limit",
    }
    raw_values = {"status_raw": "resting"}

    status, side, action, order_type = ResponseParser._parse_enum_fields(payload, raw_values)

    assert status.value == "resting"
    assert side.value == "yes"
    assert action.value == "buy"
    assert order_type.value == "limit"


def test_parse_enum_fields_invalid_value():
    payload = {
        "side": "invalid_side",
        "action": "buy",
        "type": "limit",
    }
    raw_values = {"status_raw": "resting"}

    with pytest.raises(KalshiClientError) as exc_info:
        ResponseParser._parse_enum_fields(payload, raw_values)

    assert "Unknown enum value" in str(exc_info.value)


def test_validate_required_fields_missing_field():
    payload = {"order_id": "123"}  # Missing many required fields

    with pytest.raises(KalshiClientError):
        ResponseParser._validate_required_fields(payload)


def test_validate_trade_metadata_missing_order_id():
    with pytest.raises(KalshiClientError) as exc_info:
        ResponseParser._validate_trade_metadata("rule", "reason", {})

    assert "missing order_id" in str(exc_info.value)


def test_validate_trade_metadata_missing_rule():
    with pytest.raises(KalshiClientError) as exc_info:
        ResponseParser._validate_trade_metadata(None, "reason", {"order_id": "123"})

    assert "missing trade rule/reason" in str(exc_info.value)


def test_validate_trade_metadata_missing_reason():
    with pytest.raises(KalshiClientError) as exc_info:
        ResponseParser._validate_trade_metadata("rule", None, {"order_id": "123"})

    assert "missing trade rule/reason" in str(exc_info.value)


def test_validate_trade_metadata_empty_rule():
    with pytest.raises(KalshiClientError) as exc_info:
        ResponseParser._validate_trade_metadata("", "reason", {"order_id": "123"})

    assert "missing trade rule/reason" in str(exc_info.value)


def test_parse_timestamp_delegates():
    with patch("common.kalshi_api.response_parser.ResponseFieldParser") as mock_parser:
        mock_parser.parse_timestamp.return_value = datetime(2024, 1, 1)

        result = ResponseParser.parse_timestamp("2024-01-01T00:00:00Z")

        mock_parser.parse_timestamp.assert_called_once_with("2024-01-01T00:00:00Z")
        assert result == datetime(2024, 1, 1)
