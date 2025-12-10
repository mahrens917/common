"""Tests for trade record builder."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from common.data_models.trading import OrderSide
from common.order_execution.finalizer_helpers.trade_record_builder import (
    build_trade_record,
)


class TestBuildTradeRecord:
    """Tests for build_trade_record function."""

    def test_builds_record_with_yes_side(self) -> None:
        """Builds trade record with YES side."""
        order_request = MagicMock()
        order_request.ticker = "TICKER-123"
        order_request.side = OrderSide.YES
        order_request.trade_rule = "rule_1"
        order_request.trade_reason = "test reason"

        order_response = MagicMock()
        order_response.order_id = "order-123"
        order_response.fees_cents = 5

        outcome = MagicMock()
        outcome.average_price_cents = 50
        outcome.total_filled = 10

        trade_timestamp = datetime(2025, 1, 15, 12, 0, 0)

        result = build_trade_record(
            order_request,
            order_response,
            outcome,
            "weather",
            "KPHX",
            trade_timestamp,
        )

        assert result.order_id == "order-123"
        assert result.market_ticker == "TICKER-123"
        assert result.trade_side.value == "yes"
        assert result.quantity == 10
        assert result.price_cents == 50
        assert result.fee_cents == 5
        assert result.cost_cents == 505  # 50 * 10 + 5

    def test_builds_record_with_no_side(self) -> None:
        """Builds trade record with NO side."""
        order_request = MagicMock()
        order_request.ticker = "TICKER-456"
        order_request.side = OrderSide.NO
        order_request.trade_rule = "rule_2"
        order_request.trade_reason = "another reason"

        order_response = MagicMock()
        order_response.order_id = "order-456"
        order_response.fees_cents = 3

        outcome = MagicMock()
        outcome.average_price_cents = 40
        outcome.total_filled = 5

        trade_timestamp = datetime(2025, 1, 15, 12, 0, 0)

        result = build_trade_record(
            order_request,
            order_response,
            outcome,
            "weather",
            "KJFK",
            trade_timestamp,
        )

        assert result.trade_side.value == "no"

    def test_handles_none_fees(self) -> None:
        """Treats None fees as zero."""
        order_request = MagicMock()
        order_request.ticker = "TICKER-789"
        order_request.side = OrderSide.YES
        order_request.trade_rule = "rule_3"
        order_request.trade_reason = "testing none fees behavior"

        order_response = MagicMock()
        order_response.order_id = "order-789"
        order_response.fees_cents = None

        outcome = MagicMock()
        outcome.average_price_cents = 60
        outcome.total_filled = 8

        result = build_trade_record(
            order_request,
            order_response,
            outcome,
            "weather",
            "KLAX",
            datetime.now(),
        )

        assert result.fee_cents == 0
        assert result.cost_cents == 480  # 60 * 8 + 0

    def test_handles_missing_trade_metadata(self) -> None:
        """Raises ValueError when trade metadata is missing."""
        order_request = MagicMock(spec=[])  # No trade_rule or trade_reason
        order_request.ticker = "TICKER"
        order_request.side = OrderSide.YES

        order_response = MagicMock()
        order_response.order_id = "order"
        order_response.fees_cents = 0

        outcome = MagicMock()
        outcome.average_price_cents = 50
        outcome.total_filled = 1

        with pytest.raises(ValueError, match="Trade rule must be specified"):
            build_trade_record(
                order_request,
                order_response,
                outcome,
                "weather",
                "KSFO",
                datetime.now(),
            )

    def test_includes_all_fields(self) -> None:
        """Includes all required fields in trade record."""
        order_request = MagicMock()
        order_request.ticker = "TICKER"
        order_request.side = OrderSide.YES
        order_request.trade_rule = "rule_5"
        order_request.trade_reason = "testing all fields"

        order_response = MagicMock()
        order_response.order_id = "order"
        order_response.fees_cents = 2

        outcome = MagicMock()
        outcome.average_price_cents = 55
        outcome.total_filled = 3

        trade_timestamp = datetime(2025, 1, 15, 12, 30, 0)

        result = build_trade_record(
            order_request,
            order_response,
            outcome,
            "weather",
            "KORD",
            trade_timestamp,
        )

        assert result.market_category == "weather"
        assert result.weather_station == "KORD"
        assert result.trade_timestamp == trade_timestamp
