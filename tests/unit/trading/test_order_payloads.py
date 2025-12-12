"""Tests for order payload building."""

import pytest

from common.data_models.trading import OrderAction, OrderRequest, OrderSide, OrderType, TimeInForce
from common.trading.order_payloads import build_order_payload


class TestBuildOrderPayload:
    """Tests for build_order_payload function."""

    def test_builds_valid_yes_side_payload(self):
        """Build payload for YES side order."""
        order = OrderRequest(
            ticker="TEST-24DEC",
            action=OrderAction.BUY,
            side=OrderSide.YES,
            yes_price_cents=50,
            count=10,
            client_order_id="test123",
            order_type=OrderType.LIMIT,
            time_in_force=TimeInForce.GOOD_TILL_CANCELLED,
        )
        result = build_order_payload(order)
        assert result["yes_price"] == 50
        assert "no_price" not in result

    def test_builds_valid_no_side_payload(self):
        """Build payload for NO side order."""
        order = OrderRequest(
            ticker="TEST-24DEC",
            action=OrderAction.BUY,
            side=OrderSide.NO,
            yes_price_cents=30,
            count=10,
            client_order_id="test456",
            order_type=OrderType.LIMIT,
            time_in_force=TimeInForce.GOOD_TILL_CANCELLED,
        )
        result = build_order_payload(order)
        assert result["no_price"] == 30
        assert "yes_price" not in result

    def test_includes_expiration_when_provided(self):
        """Include expiration_ts in payload when provided."""
        order = OrderRequest(
            ticker="TEST-24DEC",
            action=OrderAction.BUY,
            side=OrderSide.YES,
            yes_price_cents=50,
            count=10,
            client_order_id="test789",
            order_type=OrderType.LIMIT,
            time_in_force=TimeInForce.GOOD_TILL_CANCELLED,
            expiration_ts=1234567890,
        )
        result = build_order_payload(order)
        assert result["expiration_ts"] == 1234567890

    def test_raises_on_price_too_high(self):
        """Raise ValueError when price exceeds maximum."""
        with pytest.raises(ValueError, match="Yes price must be between 1-99 cents"):
            OrderRequest(
                ticker="TEST-24DEC",
                action=OrderAction.BUY,
                side=OrderSide.YES,
                yes_price_cents=100,
                count=10,
                client_order_id="test_fail",
                order_type=OrderType.LIMIT,
                time_in_force=TimeInForce.GOOD_TILL_CANCELLED,
            )

    def test_raises_on_negative_price(self):
        """Raise ValueError when price is negative."""
        with pytest.raises(ValueError, match="Yes price must be between 1-99 cents"):
            OrderRequest(
                ticker="TEST-24DEC",
                action=OrderAction.BUY,
                side=OrderSide.YES,
                yes_price_cents=-1,
                count=10,
                client_order_id="test_negative",
                order_type=OrderType.LIMIT,
                time_in_force=TimeInForce.GOOD_TILL_CANCELLED,
            )

    def test_raises_on_zero_price_for_limit_order(self):
        """Raise ValueError when zero price is used for non-market order."""
        with pytest.raises(ValueError, match="Yes price must be between 1-99 cents"):
            OrderRequest(
                ticker="TEST-24DEC",
                action=OrderAction.BUY,
                side=OrderSide.YES,
                yes_price_cents=0,
                count=10,
                client_order_id="test_zero",
                order_type=OrderType.LIMIT,
                time_in_force=TimeInForce.GOOD_TILL_CANCELLED,
            )
