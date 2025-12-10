"""Tests for data builder."""

from __future__ import annotations

from unittest.mock import MagicMock

from common.data_models.trading import OrderStatus
from common.order_execution.finalizer_helpers.data_builder import (
    build_order_data_payload,
    build_response_data_payload,
)

FILLED_COUNT_FIVE = 5
REMAINING_COUNT_THREE = 3
FILLED_COUNT_TEN = 10
REMAINING_COUNT_ZERO = 0
REMAINING_COUNT_TEN = 10
FILLED_COUNT_ZERO = 0
REMAINING_COUNT_FIVE = 5


class TestBuildOrderDataPayload:
    """Tests for build_order_data_payload function."""

    def test_builds_payload_with_all_fields(self) -> None:
        """Builds payload with all required fields."""
        order_request = MagicMock()
        order_request.ticker = "TICKER-123"
        order_request.action.value = "buy"
        order_request.side.value = "yes"
        order_request.yes_price_cents = 50

        order_response = MagicMock()
        order_response.filled_count = FILLED_COUNT_FIVE
        order_response.remaining_count = REMAINING_COUNT_THREE
        order_response.client_order_id = "client-123"

        result = build_order_data_payload(order_request, order_response)

        assert result["ticker"] == "TICKER-123"
        assert result["action"] == "buy"
        assert result["side"] == "yes"
        assert result["yes_price_cents"] == 50
        assert result["count"] == FILLED_COUNT_FIVE + REMAINING_COUNT_THREE
        assert result["client_order_id"] == "client-123"

    def test_count_is_sum_of_filled_and_remaining(self) -> None:
        """Count is sum of filled_count and remaining_count."""
        order_request = MagicMock()
        order_request.ticker = "TICKER"
        order_request.action.value = "sell"
        order_request.side.value = "no"
        order_request.yes_price_cents = 75

        order_response = MagicMock()
        order_response.filled_count = FILLED_COUNT_TEN
        order_response.remaining_count = REMAINING_COUNT_ZERO
        order_response.client_order_id = "id-456"

        result = build_order_data_payload(order_request, order_response)

        assert result["count"] == FILLED_COUNT_TEN


class TestBuildResponseDataPayload:
    """Tests for build_response_data_payload function."""

    def test_builds_payload_with_enum_status(self) -> None:
        """Builds payload when status is OrderStatus enum."""
        order_response = MagicMock()
        order_response.order_id = "order-123"
        order_response.status = OrderStatus.FILLED
        order_response.filled_count = FILLED_COUNT_TEN
        order_response.remaining_count = REMAINING_COUNT_ZERO
        order_response.average_fill_price_cents = 55
        order_response.fees_cents = 5

        result = build_response_data_payload(order_response)

        assert result["order_id"] == "order-123"
        assert result["status"] == "filled"
        assert result["filled_count"] == FILLED_COUNT_TEN
        assert result["remaining_count"] == REMAINING_COUNT_ZERO
        assert result["average_fill_price_cents"] == 55
        assert result["fees_cents"] == 5

    def test_builds_payload_with_string_status(self) -> None:
        """Builds payload when status is already a string."""
        order_response = MagicMock()
        order_response.order_id = "order-456"
        order_response.status = "pending"
        order_response.filled_count = FILLED_COUNT_FIVE
        order_response.remaining_count = REMAINING_COUNT_FIVE
        order_response.average_fill_price_cents = 45
        order_response.fees_cents = 3

        result = build_response_data_payload(order_response)

        assert result["status"] == "pending"

    def test_includes_all_response_fields(self) -> None:
        """Includes all required fields from response."""
        order_response = MagicMock()
        order_response.order_id = "order-789"
        order_response.status = OrderStatus.CANCELLED
        order_response.filled_count = FILLED_COUNT_ZERO
        order_response.remaining_count = REMAINING_COUNT_TEN
        order_response.average_fill_price_cents = 0
        order_response.fees_cents = 0

        result = build_response_data_payload(order_response)

        assert "order_id" in result
        assert "status" in result
        assert "filled_count" in result
        assert "remaining_count" in result
        assert "average_fill_price_cents" in result
        assert "fees_cents" in result
