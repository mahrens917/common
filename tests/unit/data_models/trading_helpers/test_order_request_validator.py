import unittest
from unittest.mock import MagicMock, Mock

from src.common.data_models.trading import OrderAction, OrderSide, OrderType, TimeInForce
from src.common.data_models.trading_helpers.order_request_validator import (
    validate_order_request_enums,
    validate_order_request_metadata,
    validate_order_request_price,
)


class TestOrderRequestValidator(unittest.TestCase):
    def test_validate_order_request_enums_success(self):
        validate_order_request_enums(
            OrderAction.BUY, OrderSide.YES, OrderType.LIMIT, TimeInForce.GOOD_TILL_CANCELLED
        )

    def test_validate_order_request_enums_failure(self):
        with self.assertRaises(TypeError):
            validate_order_request_enums(
                "BUY", OrderSide.YES, OrderType.LIMIT, TimeInForce.GOOD_TILL_CANCELLED
            )

        with self.assertRaises(TypeError):
            validate_order_request_enums(
                OrderAction.BUY, "YES", OrderType.LIMIT, TimeInForce.GOOD_TILL_CANCELLED
            )

        with self.assertRaises(TypeError):
            validate_order_request_enums(
                OrderAction.BUY, OrderSide.YES, "LIMIT", TimeInForce.GOOD_TILL_CANCELLED
            )

        with self.assertRaises(TypeError):
            validate_order_request_enums(
                OrderAction.BUY, OrderSide.YES, OrderType.LIMIT, "GOOD_TILL_CANCELLED"
            )

    def test_validate_order_request_price_limit(self):
        validate_order_request_price(OrderType.LIMIT, 50)

        with self.assertRaises(ValueError):
            validate_order_request_price(OrderType.LIMIT, None)

        with self.assertRaises(ValueError):
            validate_order_request_price(OrderType.LIMIT, 0)

        with self.assertRaises(ValueError):
            validate_order_request_price(OrderType.LIMIT, 100)

    def test_validate_order_request_price_market(self):
        validate_order_request_price(OrderType.MARKET, 50)
        validate_order_request_price(OrderType.MARKET, 0)

        with self.assertRaises(ValueError):
            validate_order_request_price(OrderType.MARKET, None)

        with self.assertRaises(ValueError):
            validate_order_request_price(OrderType.MARKET, -1)

        with self.assertRaises(ValueError):
            validate_order_request_price(OrderType.MARKET, 100)

    def test_validate_order_request_metadata_success(self):
        validate_order_request_metadata(
            "TICKER", 10, "client_id", "rule", "reason longer than 10 chars"
        )

    def test_validate_order_request_metadata_failure(self):
        with self.assertRaises(ValueError):
            validate_order_request_metadata("", 10, "client_id", "rule", "reason")

        with self.assertRaises(ValueError):
            validate_order_request_metadata("TICKER", 0, "client_id", "rule", "reason")

        with self.assertRaises(ValueError):
            validate_order_request_metadata("TICKER", 10, "", "rule", "reason")

        with self.assertRaises(ValueError):
            validate_order_request_metadata("TICKER", 10, "client_id", "", "reason")

        with self.assertRaises(ValueError):
            validate_order_request_metadata("TICKER", 10, "client_id", "rule", "")

        with self.assertRaises(ValueError):
            validate_order_request_metadata("TICKER", 10, "client_id", "rule", "short")
