import unittest
from unittest.mock import Mock

from common.data_models.trade_record import PnLBreakdown
from common.report_generator_helpers.statistics_calculator import StatisticsCalculator


class TestStatisticsCalculator(unittest.TestCase):
    def test_calculate_roi(self):
        self.assertEqual(StatisticsCalculator.calculate_roi(10, 100), 10.0)
        self.assertEqual(StatisticsCalculator.calculate_roi(0, 100), 0.0)
        self.assertEqual(StatisticsCalculator.calculate_roi(10, 0), 0.0)

    def test_calculate_average_pnl_per_trade(self):
        self.assertEqual(StatisticsCalculator.calculate_average_pnl_per_trade(100, 10), 10.0)
        self.assertEqual(StatisticsCalculator.calculate_average_pnl_per_trade(100, 0), 0.0)

    def test_get_best_performer(self):
        breakdown = {
            "A": Mock(pnl_cents=1000),
            "B": Mock(pnl_cents=2000),
            "C": Mock(pnl_cents=500),
        }
        self.assertEqual(StatisticsCalculator.get_best_performer(breakdown), "B ($+20.00)")
        self.assertEqual(StatisticsCalculator.get_best_performer({}), "N/A")

    def test_calculate_win_rate(self):
        mock_trade1 = Mock()
        mock_trade1.is_winning_trade.return_value = True
        mock_trade2 = Mock()
        mock_trade2.is_winning_trade.return_value = False

        self.assertEqual(StatisticsCalculator.calculate_win_rate([mock_trade1, mock_trade2]), 0.5)
        self.assertEqual(StatisticsCalculator.calculate_win_rate([]), 0.0)
