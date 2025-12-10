import unittest
from datetime import datetime
from unittest.mock import MagicMock, Mock

from common.data_models.trading import OrderAction, OrderSide, OrderStatus, OrderType
from common.data_models.trading_helpers.order_response_validator import (
    validate_order_response_counts,
    validate_order_response_enums,
    validate_order_response_fills,
    validate_order_response_metadata,
    validate_order_response_price,
)


class TestOrderResponseValidator(unittest.TestCase):
    def test_validate_order_response_enums_success(self):
        validate_order_response_enums(
            OrderStatus.FILLED, OrderSide.YES, OrderAction.BUY, OrderType.LIMIT
        )

    def test_validate_order_response_enums_failure(self):
        with self.assertRaises(TypeError):
            validate_order_response_enums("FILLED", OrderSide.YES, OrderAction.BUY, OrderType.LIMIT)

        with self.assertRaises(TypeError):
            validate_order_response_enums(
                OrderStatus.FILLED, "YES", OrderAction.BUY, OrderType.LIMIT
            )

        with self.assertRaises(TypeError):
            validate_order_response_enums(OrderStatus.FILLED, OrderSide.YES, "BUY", OrderType.LIMIT)

        with self.assertRaises(TypeError):
            validate_order_response_enums(
                OrderStatus.FILLED, OrderSide.YES, OrderAction.BUY, "LIMIT"
            )

    def test_validate_order_response_counts_success(self):
        validate_order_response_counts(10, 0, OrderStatus.FILLED)
        validate_order_response_counts(0, 10, OrderStatus.PENDING)

    def test_validate_order_response_counts_failure(self):
        with self.assertRaises(ValueError):
            validate_order_response_counts(-1, 0, OrderStatus.FILLED)

        with self.assertRaises(ValueError):
            validate_order_response_counts(10, -1, OrderStatus.FILLED)

        with self.assertRaises(ValueError):
            validate_order_response_counts(0, 0, OrderStatus.FILLED)

    def test_validate_order_response_price_success(self):
        validate_order_response_price(10, 50, 5)
        validate_order_response_price(10, None, 5)  # None is allowed
        validate_order_response_price(0, None, 0)

    def test_validate_order_response_price_failure(self):
        with self.assertRaises(ValueError):
            validate_order_response_price(10, 0, 5)

        with self.assertRaises(ValueError):
            validate_order_response_price(10, 100, 5)

        with self.assertRaises(ValueError):
            validate_order_response_price(10, 50, -1)

    def test_validate_order_response_fills_success(self):
        fill1 = Mock(count=5)
        fill2 = Mock(count=5)
        validate_order_response_fills([fill1, fill2], 10)
        validate_order_response_fills([], 0)

    def test_validate_order_response_fills_failure(self):
        fill1 = Mock(count=5)
        with self.assertRaises(ValueError):
            validate_order_response_fills([fill1], 10)

    def test_validate_order_response_metadata_success(self):
        validate_order_response_metadata(
            "order_id", "client_id", "ticker", "rule", "reason longer than 10", datetime.now()
        )

    def test_validate_order_response_metadata_failure(self):
        with self.assertRaises(ValueError):
            validate_order_response_metadata(
                "", "client_id", "ticker", "rule", "reason", datetime.now()
            )

        with self.assertRaises(ValueError):
            validate_order_response_metadata(
                "order_id", "", "ticker", "rule", "reason", datetime.now()
            )

        with self.assertRaises(ValueError):
            validate_order_response_metadata(
                "order_id", "client_id", "", "rule", "reason", datetime.now()
            )

        with self.assertRaises(TypeError):
            validate_order_response_metadata(
                "order_id", "client_id", "ticker", "rule", "reason", "not datetime"
            )

        with self.assertRaises(ValueError):
            validate_order_response_metadata(
                "order_id", "client_id", "ticker", "", "reason", datetime.now()
            )

        with self.assertRaises(ValueError):
            validate_order_response_metadata(
                "order_id", "client_id", "ticker", "rule", "", datetime.now()
            )

        with self.assertRaises(ValueError):
            validate_order_response_metadata(
                "order_id", "client_id", "ticker", "rule", "short", datetime.now()
            )
