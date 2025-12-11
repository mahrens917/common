import unittest
from datetime import date
from unittest.mock import AsyncMock, Mock

from common.report_generator_helpers.report_delegator import ReportDelegator


class TestReportDelegator(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_coordinator = Mock()
        self.mock_summary_builder = Mock()
        self.mock_unified_builder = Mock()
        self.delegator = ReportDelegator(
            self.mock_coordinator,
            self.mock_summary_builder,
            self.mock_unified_builder,
        )

    async def test_generate_daily_report_success(self):
        self.mock_coordinator.generate_daily_report = AsyncMock(return_value="Report")
        result = await self.delegator.generate_daily_report(date(2023, 1, 1))
        self.assertEqual(result, "Report")

    async def test_generate_daily_report_failure(self):
        self.mock_coordinator.generate_daily_report = AsyncMock(side_effect=ValueError("Error"))
        result = await self.delegator.generate_daily_report(date(2023, 1, 1))
        self.assertIn("❌ Error generating daily report", result)

    async def test_generate_historical_report_success(self):
        self.mock_coordinator.generate_historical_report = AsyncMock(return_value="History")
        result = await self.delegator.generate_historical_report(date(2023, 1, 1), date(2023, 1, 2))
        self.assertEqual(result, "History")

    async def test_generate_historical_report_failure(self):
        self.mock_coordinator.generate_historical_report = AsyncMock(side_effect=KeyError("Error"))
        result = await self.delegator.generate_historical_report(date(2023, 1, 1), date(2023, 1, 2))
        self.assertIn("❌ Error generating historical report", result)

    async def test_generate_current_day_report_success(self):
        self.mock_coordinator.generate_current_day_report = AsyncMock(return_value="Current")
        result = await self.delegator.generate_current_day_report()
        self.assertEqual(result, "Current")

    async def test_generate_current_day_report_failure(self):
        self.mock_coordinator.generate_current_day_report = AsyncMock(side_effect=TypeError("Error"))
        result = await self.delegator.generate_current_day_report()
        self.assertIn("❌ Error generating current day report", result)

    async def test_generate_settlement_notification(self):
        self.mock_summary_builder.generate_settlement_notification = AsyncMock(return_value="Notif")
        result = await self.delegator.generate_settlement_notification(date(2023, 1, 1), [], "Daily")
        self.assertEqual(result, "Notif")

    async def test_generate_summary_stats_success(self):
        self.mock_summary_builder.generate_summary_stats = AsyncMock(return_value="Stats")
        result = await self.delegator.generate_summary_stats(30)
        self.assertEqual(result, "Stats")

    async def test_generate_summary_stats_failure(self):
        self.mock_summary_builder.generate_summary_stats = AsyncMock(side_effect=ValueError("Error"))
        result = await self.delegator.generate_summary_stats(30)
        self.assertIn("❌ Error generating summary statistics", result)

    async def test_generate_unified_pnl_report_success(self):
        self.mock_unified_builder.generate_unified_pnl_report = AsyncMock(return_value="Unified")
        result = await self.delegator.generate_unified_pnl_report()
        self.assertEqual(result, "Unified")

    async def test_generate_unified_pnl_report_failure(self):
        self.mock_unified_builder.generate_unified_pnl_report = AsyncMock(side_effect=ValueError("Error"))
        result = await self.delegator.generate_unified_pnl_report()
        self.assertIn("❌ Error generating unified P&L report", result)

    async def test_generate_unified_pnl_data_success(self):
        self.mock_unified_builder.generate_unified_pnl_data = AsyncMock(return_value={"data": 1})
        result = await self.delegator.generate_unified_pnl_data()
        self.assertEqual(result, {"data": 1})

    async def test_generate_unified_pnl_data_failure(self):
        self.mock_unified_builder.generate_unified_pnl_data = AsyncMock(side_effect=ValueError("Error"))
        with self.assertRaises(ValueError):
            await self.delegator.generate_unified_pnl_data()
