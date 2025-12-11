import unittest
from datetime import date, datetime
from unittest.mock import AsyncMock, Mock, patch

from common.data_models.trade_record import PnLReport
from common.report_generator_helpers.summary_report_builder import SummaryReportBuilder


class TestSummaryReportBuilder(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_pnl_calculator = Mock()
        self.mock_stats_calculator = Mock()
        self.timezone = "UTC"
        self.builder = SummaryReportBuilder(
            self.mock_pnl_calculator,
            self.mock_stats_calculator,
            self.timezone,
        )

    @patch("common.report_generator_helpers.summary_report_builder.get_timezone_aware_date")
    async def test_generate_summary_stats(self, mock_get_date):
        mock_now = datetime(2023, 10, 31)
        mock_get_date.return_value = mock_now

        mock_report = Mock(spec=PnLReport)
        mock_report.total_pnl_cents = 5000
        mock_report.total_cost_cents = 10000
        mock_report.total_trades = 10
        mock_report.win_rate = 0.6
        mock_report.by_weather_station = {"station": "data"}
        mock_report.by_rule = {"rule": "data"}

        self.mock_pnl_calculator.generate_aggregated_report = AsyncMock(return_value=mock_report)
        self.mock_stats_calculator.calculate_roi.return_value = 50.0
        self.mock_stats_calculator.calculate_average_pnl_per_trade.return_value = 5.0
        self.mock_stats_calculator.get_best_performer.side_effect = ["Best Station", "Best Rule"]

        result = await self.builder.generate_summary_stats(30)

        self.assertIn("📈 **30-Day Summary**", result)
        self.assertIn("💰 Total P&L: $50.00", result)
        self.assertIn("📊 ROI: +50.0%", result)
        self.assertIn("📈 Total Trades: 10", result)
        self.assertIn("🎯 Win Rate: 60.0%", result)
        self.assertIn("💵 Avg P&L/Trade: $5.00", result)
        self.assertIn("🏆 Best Station: Best Station", result)
        self.assertIn("⭐ Best Rule: Best Rule", result)

    async def test_generate_settlement_notification(self):
        trade_date = date(2023, 10, 27)
        settled_markets = ["MKT1", "MKT2"]
        daily_report = "Daily Report Content"

        result = await self.builder.generate_settlement_notification(trade_date, settled_markets, daily_report)

        self.assertIn(f"🔔 **Settlement Alert - {trade_date.strftime('%B %d, %Y')}**", result)
        self.assertIn("✅ 2 markets have settled", result)
        self.assertIn("Daily Report Content", result)
