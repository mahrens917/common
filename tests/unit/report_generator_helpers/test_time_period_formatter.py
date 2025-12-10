import unittest
from unittest.mock import Mock

from common.data_models.trade_record import PnLReport
from common.report_generator_helpers.time_period_formatter import TimePeriodFormatter


class TestTimePeriodFormatter(unittest.TestCase):
    def setUp(self):
        self.mock_emoji_selector = Mock()
        self.mock_dollar_converter = Mock()
        self.formatter = TimePeriodFormatter(self.mock_emoji_selector, self.mock_dollar_converter)

    def test_format_time_period_section(self):
        mock_report = Mock(spec=PnLReport)
        mock_report.total_pnl_cents = 5000
        mock_report.total_cost_cents = 10000
        mock_report.total_trades = 10
        mock_report.win_rate = 0.6

        self.mock_dollar_converter.calculate_total_contracts.return_value = 20
        self.mock_emoji_selector.get_fire_or_cold_emoji.return_value = "🔥"

        result = self.formatter.format_time_period_section(
            mock_report, "Test Period", include_unrealized=True, unrealized_pnl_cents=1000
        )

        self.assertIn("🔥 **Test Period**", result)
        self.assertIn("├── P&L: $+50.00 (10 trades)", result)
        self.assertIn("├── Unrealized P&L: $+10.00 (market-based)", result)
        self.assertIn("├── Contracts Traded: 20", result)
        self.assertIn("├── Money Traded: $100.00", result)
        self.assertIn("├── Total P&L (%): $+60.00 (+60.0%)", result)
        self.assertIn("└── Win Rate: 60% (10 trades)", result)

    def test_format_time_period_section_with_days_count(self):
        mock_report = Mock(spec=PnLReport)
        mock_report.total_pnl_cents = 7000
        mock_report.total_cost_cents = 10000
        mock_report.total_trades = 10
        mock_report.win_rate = 0.6

        self.mock_dollar_converter.calculate_total_contracts.return_value = 20
        self.mock_emoji_selector.get_fire_or_cold_emoji.return_value = "🔥"

        result = self.formatter.format_time_period_section(mock_report, "7-Day Trend", days_count=7)

        self.assertIn("🔥 **7-Day Trend**", result)
        self.assertIn("└── Daily Avg: $+10.00 (+10.0%)", result)

    def test_format_time_period_section_zero_cost(self):
        mock_report = Mock(spec=PnLReport)
        mock_report.total_pnl_cents = 5000
        mock_report.total_cost_cents = 0
        mock_report.total_trades = 10
        mock_report.win_rate = 0.6

        self.mock_dollar_converter.calculate_total_contracts.return_value = 20
        self.mock_emoji_selector.get_fire_or_cold_emoji.return_value = "🔥"

        result = self.formatter.format_time_period_section(mock_report, "Test Period")

        self.assertIn("├── Total P&L (%): $+50.00", result)
        self.assertNotIn("(+", result)  # No percentage
