"""Tests for order_parser module."""

from unittest.mock import MagicMock, patch

import pytest

from common.kalshi_trading_client.services.order_helpers.order_parser import OrderParser
from common.trading_exceptions import KalshiDataIntegrityError

_TEST_PARTIAL_FILL = 5
_TEST_FULL_FILL = 10
_TEST_ZERO_REMAINING = 0


class TestOrderParser:
    """Tests for OrderParser class."""

    def test_parse_order_response_success_with_order_key(self):
        mock_order_response = MagicMock()
        mock_order_response.order_id = "order-123"
        mock_order_response.status.value = "resting"
        mock_order_response.filled_count = _TEST_PARTIAL_FILL
        mock_order_response.remaining_count = _TEST_PARTIAL_FILL

        with patch("common.order_response_parser.validate_order_response_schema") as mock_validate:
            with patch("common.order_response_parser.parse_kalshi_order_response") as mock_parse:
                mock_validate.return_value = {"order_id": "order-123"}
                mock_parse.return_value = mock_order_response

                result = OrderParser.parse_order_response(
                    {"order": {"order_id": "order-123"}},
                    "test_operation",
                    "weather_rule",
                    "temperature_high",
                )

                assert result.order_id == "order-123"
                mock_validate.assert_called_once()

    def test_parse_order_response_success_without_order_key(self):
        mock_order_response = MagicMock()
        mock_order_response.order_id = "order-456"
        mock_order_response.status.value = "filled"
        mock_order_response.filled_count = _TEST_FULL_FILL
        mock_order_response.remaining_count = _TEST_ZERO_REMAINING

        with patch("common.order_response_parser.parse_kalshi_order_response") as mock_parse:
            mock_parse.return_value = mock_order_response

            result = OrderParser.parse_order_response(
                {"order_id": "order-456", "status": "filled"},
                "test_operation",
                "weather_rule",
                "temperature_high",
            )

            assert result.order_id == "order-456"

    def test_parse_order_response_value_error(self):
        with patch("common.order_response_parser.parse_kalshi_order_response") as mock_parse:
            mock_parse.side_effect = ValueError("Invalid order data")

            with pytest.raises(KalshiDataIntegrityError, match="Order response validation failed"):
                OrderParser.parse_order_response(
                    {"invalid": "data"},
                    "test_operation",
                    "rule",
                    "reason",
                )

    def test_parse_order_response_key_error(self):
        with patch("common.order_response_parser.parse_kalshi_order_response") as mock_parse:
            mock_parse.side_effect = KeyError("missing_key")

            with pytest.raises(KalshiDataIntegrityError, match="Unexpected error parsing"):
                OrderParser.parse_order_response(
                    {"partial": "data"},
                    "test_operation",
                    "rule",
                    "reason",
                )

    def test_parse_order_response_type_error(self):
        with patch("common.order_response_parser.parse_kalshi_order_response") as mock_parse:
            mock_parse.side_effect = TypeError("Type mismatch")

            with pytest.raises(KalshiDataIntegrityError, match="Unexpected error parsing"):
                OrderParser.parse_order_response(
                    {"bad": "types"},
                    "test_operation",
                    "rule",
                    "reason",
                )
