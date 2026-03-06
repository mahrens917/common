"""Tests for kalshi_api response_parser."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from common.kalshi_api.client_helpers.errors import KalshiClientError
from common.kalshi_api.response_parser import (
    _parse_enum_fields,
    _validate_required_fields,
    _validate_trade_metadata,
    normalise_rp_fill,
    parse_order_response,
    parse_rp_order_fill,
    parse_rp_timestamp,
)


def test_parse_order_fill_delegates():
    with patch("common.kalshi_api.response_parser.parse_order_fill") as mock_fn:
        mock_fn.return_value = MagicMock()

        parse_rp_order_fill({"fill": "data"})

        mock_fn.assert_called_once_with({"fill": "data"})


def test_normalise_fill_delegates():
    with patch("common.kalshi_api.response_parser.normalise_fill") as mock_fn:
        mock_fn.return_value = {"normalized": True}

        result = normalise_rp_fill({"raw": "data"})

        mock_fn.assert_called_once_with({"raw": "data"})
        assert result == {"normalized": True}


def test_parse_enum_fields_success():
    payload = {
        "side": "yes",
        "action": "buy",
        "type": "limit",
    }
    raw_values = {"status_raw": "resting"}

    status, side, action, order_type = _parse_enum_fields(payload, raw_values)

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
        _parse_enum_fields(payload, raw_values)

    assert "Unknown enum value" in str(exc_info.value)


def test_validate_required_fields_missing_field():
    payload = {"order_id": "123"}  # Missing many required fields

    with pytest.raises(KalshiClientError):
        _validate_required_fields(payload)


def test_validate_trade_metadata_missing_order_id():
    with pytest.raises(KalshiClientError) as exc_info:
        _validate_trade_metadata("rule", "reason", {})

    assert "missing order_id" in str(exc_info.value)


def test_validate_trade_metadata_missing_rule():
    with pytest.raises(KalshiClientError) as exc_info:
        _validate_trade_metadata(None, "reason", {"order_id": "123"})

    assert "missing trade rule/reason" in str(exc_info.value)


def test_validate_trade_metadata_missing_reason():
    with pytest.raises(KalshiClientError) as exc_info:
        _validate_trade_metadata("rule", None, {"order_id": "123"})

    assert "missing trade rule/reason" in str(exc_info.value)


def test_validate_trade_metadata_empty_rule():
    with pytest.raises(KalshiClientError) as exc_info:
        _validate_trade_metadata("", "reason", {"order_id": "123"})

    assert "missing trade rule/reason" in str(exc_info.value)


def test_parse_order_response_success():
    ts = "2024-01-01T00:00:00Z"
    payload = {
        "order_id": "ORD123",
        "client_order_id": "CID456",
        "status": "resting",
        "filled_count": 0,
        "remaining_count": 5,
        "fees": 10,
        "timestamp": ts,
        "fills": [],
        "ticker": "KXTEST-T50",
        "side": "yes",
        "action": "buy",
        "type": "limit",
    }
    result = parse_order_response(payload, "test_rule", "test_reason")
    assert result.order_id == "ORD123"
    assert result.ticker == "KXTEST-T50"
    assert result.trade_rule == "test_rule"
    assert result.trade_reason == "test_reason"


def test_parse_timestamp_delegates():
    with patch("common.kalshi_api.response_parser.parse_rfp_timestamp") as mock_fn:
        mock_fn.return_value = datetime(2024, 1, 1)

        result = parse_rp_timestamp("2024-01-01T00:00:00Z")

        mock_fn.assert_called_once_with("2024-01-01T00:00:00Z")
        assert result == datetime(2024, 1, 1)
