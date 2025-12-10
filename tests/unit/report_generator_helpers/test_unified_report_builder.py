import unittest
from datetime import date, datetime
from unittest.mock import AsyncMock, Mock, patch

from common.data_models.trade_record import PnLBreakdown, PnLReport
from common.report_generator_helpers.unified_report_builder import UnifiedReportBuilder


class TestUnifiedReportBuilder(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_pnl_calculator = Mock()
        self.mock_trade_store = Mock()
        self.mock_pnl_calculator.trade_store = self.mock_trade_store
        self.mock_unified_formatter = Mock()
        self.mock_time_period_formatter = Mock()
        self.mock_daily_collector = Mock()
        self.timezone = "UTC"
        self.builder = UnifiedReportBuilder(
            self.mock_pnl_calculator,
            self.mock_unified_formatter,
            self.mock_time_period_formatter,
            self.mock_daily_collector,
            self.timezone,
        )

    @patch("common.report_generator_helpers.unified_report_builder.get_timezone_aware_date")
    async def test_generate_unified_pnl_report(self, mock_get_date):
        mock_now = datetime(2023, 10, 31)
        mock_get_date.return_value = mock_now

        self.mock_pnl_calculator.get_today_unified_pnl = AsyncMock(return_value=1000)
        self.mock_pnl_calculator.get_yesterday_unified_pnl = AsyncMock(return_value=2000)
        self.mock_trade_store.get_trades_by_date_range = AsyncMock(side_effect=[["t1"], ["t2"]])
        self.mock_pnl_calculator.get_date_range_trades_and_report = AsyncMock(
            side_effect=[
                (["t3"], "report7"),
                (["t4"], "report30"),
            ]
        )

        self.mock_unified_formatter.format_unified_pnl_section.return_value = "Unified Section"
        self.mock_time_period_formatter.format_time_period_section.return_value = "Time Section"

        result = await self.builder.generate_unified_pnl_report()

        self.assertIn("📊 **Trading Performance Summary**", result)
        self.assertIn("Unified Section", result)
        self.assertIn("Time Section", result)

        self.mock_unified_formatter.format_unified_pnl_section.assert_called()
        self.mock_time_period_formatter.format_time_period_section.assert_called()

    @patch("common.report_generator_helpers.unified_report_builder.get_timezone_aware_date")
    async def test_generate_unified_pnl_data(self, mock_get_date):
        mock_now = datetime(2023, 10, 31)
        mock_get_date.return_value = mock_now

        self.mock_daily_collector.get_daily_pnl_with_unrealized_percentage = AsyncMock(
            return_value=[(date(2023, 10, 31), 10.0)]
        )
        self.mock_daily_collector.get_daily_pnl_with_unrealized = AsyncMock(
            return_value=[(date(2023, 10, 31), 1000)]
        )

        mock_report = Mock(spec=PnLReport)
        mock_breakdown = Mock(spec=PnLBreakdown)
        mock_breakdown.pnl_cents = 5000
        mock_report.by_weather_station = {"Station1": mock_breakdown}
        mock_report.by_rule = {"Rule1": mock_breakdown}

        self.mock_pnl_calculator.get_date_range_trades_and_report = AsyncMock(
            return_value=([], mock_report)
        )

        result = await self.builder.generate_unified_pnl_data()

        self.assertEqual(result["daily_pnl"], [(date(2023, 10, 31), 10.0)])
        self.assertEqual(result["daily_pnl_dollars"], [(date(2023, 10, 31), 1000)])
        self.assertEqual(result["station_breakdown"], {"Station1": 5000})
        self.assertEqual(result["rule_breakdown"], {"Rule1": 5000})
