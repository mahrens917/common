"""Tests for validators module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.common.order_execution.finalizer_helpers.validators import (
    validate_order_metadata,
    validate_response_metadata,
)
from src.common.trading_exceptions import KalshiTradePersistenceError


class TestValidateOrderMetadata:
    """Tests for validate_order_metadata function."""

    def test_passes_when_all_metadata_present(self) -> None:
        """Passes validation when all required metadata is present."""
        order_request = MagicMock()
        order_request.trade_rule = "rule_1"
        order_request.trade_reason = "test reason"

        validate_order_metadata(order_request, "order-123", "TICKER-123", "test_op")

    def test_raises_when_trade_rule_missing(self) -> None:
        """Raises KalshiTradePersistenceError when trade_rule is missing."""
        order_request = MagicMock()
        order_request.trade_rule = None
        order_request.trade_reason = "test reason"

        with pytest.raises(KalshiTradePersistenceError, match="trade_rule"):
            validate_order_metadata(order_request, "order-123", "TICKER-123", "test_op")

    def test_raises_when_trade_reason_missing(self) -> None:
        """Raises KalshiTradePersistenceError when trade_reason is missing."""
        order_request = MagicMock()
        order_request.trade_rule = "rule_1"
        order_request.trade_reason = None

        with pytest.raises(KalshiTradePersistenceError, match="trade_reason"):
            validate_order_metadata(order_request, "order-123", "TICKER-123", "test_op")

    def test_raises_when_trade_rule_empty_string(self) -> None:
        """Raises KalshiTradePersistenceError when trade_rule is empty string."""
        order_request = MagicMock()
        order_request.trade_rule = ""
        order_request.trade_reason = "test reason"

        with pytest.raises(KalshiTradePersistenceError, match="trade_rule"):
            validate_order_metadata(order_request, "order-123", "TICKER-123", "test_op")


class TestValidateResponseMetadata:
    """Tests for validate_response_metadata function."""

    def test_passes_when_fees_present(self) -> None:
        """Passes validation when fees_cents is present."""
        order_response = MagicMock()
        order_response.fees_cents = 5

        validate_response_metadata(order_response, "order-123", "TICKER-123", "test_op")

    def test_passes_when_fees_zero(self) -> None:
        """Passes validation when fees_cents is zero."""
        order_response = MagicMock()
        order_response.fees_cents = 0

        validate_response_metadata(order_response, "order-123", "TICKER-123", "test_op")

    def test_raises_when_fees_none(self) -> None:
        """Raises KalshiTradePersistenceError when fees_cents is None."""
        order_response = MagicMock()
        order_response.fees_cents = None

        with pytest.raises(KalshiTradePersistenceError, match="fees_cents"):
            validate_response_metadata(order_response, "order-123", "TICKER-123", "test_op")
