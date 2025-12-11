import unittest
from unittest.mock import Mock

from common.report_generator_helpers.dollar_converter import DollarConverter


class TestDollarConverter(unittest.TestCase):
    def test_cents_to_dollars(self):
        self.assertEqual(DollarConverter.cents_to_dollars(100), 1.0)
        self.assertEqual(DollarConverter.cents_to_dollars(1234), 12.34)
        self.assertEqual(DollarConverter.cents_to_dollars(0), 0.0)
        self.assertEqual(DollarConverter.cents_to_dollars(-500), -5.0)

    def test_calculate_total_return(self):
        self.assertEqual(DollarConverter.calculate_total_return(1000, 500), 15.0)
        self.assertEqual(DollarConverter.calculate_total_return(1000, -200), 8.0)
        self.assertEqual(DollarConverter.calculate_total_return(0, 0), 0.0)

    def test_calculate_total_contracts(self):
        mock_trade1 = Mock()
        mock_trade1.quantity = 5
        mock_trade2 = Mock()
        mock_trade2.quantity = 10

        self.assertEqual(DollarConverter.calculate_total_contracts([mock_trade1, mock_trade2]), 15)
        self.assertEqual(DollarConverter.calculate_total_contracts([]), 0)
        self.assertEqual(DollarConverter.calculate_total_contracts(None), 0)

    def test_calculate_total_cost_dollars(self):
        mock_trade1 = Mock()
        mock_trade1.cost_cents = 500
        mock_trade2 = Mock()
        mock_trade2.cost_cents = 1500

        self.assertEqual(DollarConverter.calculate_total_cost_dollars([mock_trade1, mock_trade2]), 20.0)
        self.assertEqual(DollarConverter.calculate_total_cost_dollars([]), 0.0)
        self.assertEqual(DollarConverter.calculate_total_cost_dollars(None), 0.0)
