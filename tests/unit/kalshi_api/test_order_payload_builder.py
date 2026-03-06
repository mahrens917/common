"""Tests for order_payload_builder."""

import pytest

from common.data_models.trading import OrderAction, OrderRequest, OrderSide, OrderType, TimeInForce
from common.trading.order_payloads import build_order_payload


class TestBuildOrderPayload:
    """Tests for build_order_payload function."""

    def _make_order(self, **overrides):
        defaults = {
            "ticker": "TEST-24DEC",
            "action": OrderAction.BUY,
            "side": OrderSide.YES,
            "yes_price_cents": 50,
            "count": 10,
            "client_order_id": "test123",
            "order_type": OrderType.LIMIT,
            "time_in_force": TimeInForce.GOOD_TILL_CANCELLED,
        }
        defaults.update(overrides)
        return OrderRequest(**defaults)

    def test_yes_side_payload(self):
        result = build_order_payload(self._make_order(side=OrderSide.YES))
        assert result["yes_price"] == 50
        assert "no_price" not in result

    def test_no_side_payload(self):
        result = build_order_payload(self._make_order(side=OrderSide.NO, yes_price_cents=30))
        assert result["no_price"] == 30
        assert "yes_price" not in result

    def test_includes_expiration(self):
        result = build_order_payload(self._make_order(expiration_ts=1234567890))
        assert result["expiration_ts"] == 1234567890

    def test_omits_expiration_when_none(self):
        result = build_order_payload(self._make_order())
        assert "expiration_ts" not in result

    def test_payload_fields(self):
        order = self._make_order()
        result = build_order_payload(order)
        assert result["ticker"] == "TEST-24DEC"
        assert result["action"] == OrderAction.BUY.value
        assert result["side"] == OrderSide.YES.value
        assert result["count"] == 10
        assert result["client_order_id"] == "test123"
        assert result["type"] == OrderType.LIMIT.value
        assert result["time_in_force"] == TimeInForce.GOOD_TILL_CANCELLED.value

    def test_raises_on_none_price(self):
        order = self._make_order()
        object.__setattr__(order, "yes_price_cents", None)
        with pytest.raises(ValueError, match="must provide yes_price_cents"):
            build_order_payload(order)
