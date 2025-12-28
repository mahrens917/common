"""Tests for order_validator module."""

import uuid
from unittest.mock import MagicMock

import pytest

from common.data_models.trading import OrderAction, OrderRequest, OrderSide, OrderType
from common.kalshi_trading_client.services.order_helpers.order_validator import OrderValidator
from common.trading_exceptions import KalshiOrderValidationError


class TestOrderValidator:
    """Tests for OrderValidator class."""

    def test_validate_order_request_success(self):
        order = OrderRequest(
            ticker="TICKER-ABC-123",
            client_order_id=str(uuid.uuid4()),
            side=OrderSide.YES,
            action=OrderAction.BUY,
            count=10,
            order_type=OrderType.LIMIT,
            yes_price_cents=50,
        )

        OrderValidator.validate_order_request(order)

    def test_validate_order_request_empty_ticker(self):
        order = MagicMock(spec=OrderRequest)
        order.ticker = ""
        order.client_order_id = str(uuid.uuid4())
        order.__dict__ = {"ticker": "", "client_order_id": order.client_order_id}

        with pytest.raises(KalshiOrderValidationError, match="Invalid ticker"):
            OrderValidator.validate_order_request(order)

    def test_validate_order_request_short_ticker(self):
        order = MagicMock(spec=OrderRequest)
        order.ticker = "AB"
        order.client_order_id = str(uuid.uuid4())
        order.__dict__ = {"ticker": "AB", "client_order_id": order.client_order_id}

        with pytest.raises(KalshiOrderValidationError, match="Invalid ticker"):
            OrderValidator.validate_order_request(order)

    def test_validate_order_request_invalid_uuid(self):
        order = MagicMock(spec=OrderRequest)
        order.ticker = "TICKER-ABC"
        order.client_order_id = "not-a-valid-uuid"
        order.__dict__ = {"ticker": "TICKER-ABC", "client_order_id": "not-a-valid-uuid"}

        with pytest.raises(KalshiOrderValidationError, match="Client order ID must be valid UUID"):
            OrderValidator.validate_order_request(order)

    def test_has_sufficient_balance_returns_true(self):
        result = OrderValidator.has_sufficient_balance_for_trade_with_fees(
            cached_balance_cents=10000,
            trade_cost_cents=5000,
            fees_cents=100,
        )

        assert result is True

    def test_has_sufficient_balance_returns_false(self):
        result = OrderValidator.has_sufficient_balance_for_trade_with_fees(
            cached_balance_cents=1000,
            trade_cost_cents=5000,
            fees_cents=100,
        )

        assert result is False

    def test_has_sufficient_balance_exact_match(self):
        result = OrderValidator.has_sufficient_balance_for_trade_with_fees(
            cached_balance_cents=5100,
            trade_cost_cents=5000,
            fees_cents=100,
        )

        assert result is True

    def test_has_sufficient_balance_one_cent_short(self):
        result = OrderValidator.has_sufficient_balance_for_trade_with_fees(
            cached_balance_cents=5099,
            trade_cost_cents=5000,
            fees_cents=100,
        )

        assert result is False
