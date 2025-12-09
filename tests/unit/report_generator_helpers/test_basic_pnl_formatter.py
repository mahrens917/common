import unittest
from unittest.mock import Mock

from src.common.data_models.trade_record import PnLReport
from src.common.report_generator_helpers.basic_pnl_formatter import BasicPnLFormatter


class TestBasicPnLFormatter(unittest.TestCase):
    def setUp(self):
        self.mock_emoji_selector = Mock()
        self.mock_station_formatter = Mock()
        self.mock_rule_formatter = Mock()
        self.formatter = BasicPnLFormatter(
            self.mock_emoji_selector,
            self.mock_station_formatter,
            self.mock_rule_formatter,
        )

    def test_format_pnl_report(self):
        # Setup mock report
        mock_report = Mock(spec=PnLReport)
        mock_report.total_pnl_cents = 5000  # $50.00
        mock_report.total_cost_cents = 10000  # $100.00
        mock_report.total_trades = 10
        mock_report.win_rate = 0.6
        mock_report.by_weather_station = {"station_data": "data"}
        mock_report.by_rule = {"rule_data": "data"}

        # Setup mock behaviors
        self.mock_emoji_selector.get_pnl_emoji.return_value = "🟢"
        self.mock_station_formatter.format_station_breakdown.return_value = ["Station Breakdown"]
        self.mock_rule_formatter.format_rule_breakdown.return_value = ["Rule Breakdown"]

        # Execute
        title = "Test Report"
        result = self.formatter.format_pnl_report(mock_report, title)

        # Verify
        self.assertIn(f"📊 **{title}**", result)
        self.assertIn("🟢 **Total: Put up $100.00, Got back $150.00, P&L $+50.00**", result)
        self.assertIn("📈 Total Trades: 10", result)
        self.assertIn("🎯 Win Rate: 60.0%", result)
        self.assertIn("Station Breakdown", result)
        self.assertIn("Rule Breakdown", result)

        self.mock_emoji_selector.get_pnl_emoji.assert_called_with(50.0)
        self.mock_station_formatter.format_station_breakdown.assert_called_with(
            mock_report.by_weather_station
        )
        self.mock_rule_formatter.format_rule_breakdown.assert_called_with(mock_report.by_rule)
