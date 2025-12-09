"""Tests for validation helper."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.common.order_execution.finalizer_helpers.validation_helper import (
    validate_order_metadata,
)
from src.common.trading_exceptions import KalshiTradePersistenceError


class TestValidateOrderMetadata:
    """Tests for validate_order_metadata function."""

    def test_passes_when_all_metadata_present(self) -> None:
        """Passes validation when all required metadata is present."""
        order_request = MagicMock()
        order_request.ticker = "TICKER-123"
        order_request.trade_rule = "rule_1"
        order_request.trade_reason = "test reason"

        order_response = MagicMock()
        order_response.order_id = "order-123"
        order_response.fees_cents = 5

        validate_order_metadata(order_request, order_response, "test_op")

    def test_raises_when_trade_rule_missing(self) -> None:
        """Raises KalshiTradePersistenceError when trade_rule is missing."""
        order_request = MagicMock()
        order_request.ticker = "TICKER-123"
        order_request.trade_rule = None
        order_request.trade_reason = "test reason"

        order_response = MagicMock()
        order_response.order_id = "order-123"
        order_response.fees_cents = 5

        with pytest.raises(KalshiTradePersistenceError, match="trade_rule"):
            validate_order_metadata(order_request, order_response, "test_op")

    def test_raises_when_trade_reason_missing(self) -> None:
        """Raises KalshiTradePersistenceError when trade_reason is missing."""
        order_request = MagicMock()
        order_request.ticker = "TICKER-123"
        order_request.trade_rule = "rule_1"
        order_request.trade_reason = None

        order_response = MagicMock()
        order_response.order_id = "order-123"
        order_response.fees_cents = 5

        with pytest.raises(KalshiTradePersistenceError, match="trade_reason"):
            validate_order_metadata(order_request, order_response, "test_op")

    def test_raises_when_fees_cents_none(self) -> None:
        """Raises KalshiTradePersistenceError when fees_cents is None."""
        order_request = MagicMock()
        order_request.ticker = "TICKER-123"
        order_request.trade_rule = "rule_1"
        order_request.trade_reason = "test reason"

        order_response = MagicMock()
        order_response.order_id = "order-123"
        order_response.fees_cents = None

        with pytest.raises(KalshiTradePersistenceError, match="fees_cents"):
            validate_order_metadata(order_request, order_response, "test_op")

    def test_checks_trade_rule_before_trade_reason(self) -> None:
        """Checks trade_rule before trade_reason (first failure wins)."""
        order_request = MagicMock()
        order_request.ticker = "TICKER-123"
        order_request.trade_rule = None
        order_request.trade_reason = None

        order_response = MagicMock()
        order_response.order_id = "order-123"
        order_response.fees_cents = 5

        with pytest.raises(KalshiTradePersistenceError, match="trade_rule"):
            validate_order_metadata(order_request, order_response, "test_op")
