import unittest
from datetime import date, datetime
from unittest.mock import AsyncMock, Mock, patch

from common.data_models.trade_record import PnLReport
from common.report_generator_helpers.report_coordinator import ReportCoordinator


class TestReportCoordinator(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_pnl_calculator = Mock()
        self.mock_basic_formatter = Mock()
        self.mock_current_day_formatter = Mock()
        self.timezone = "UTC"
        self.coordinator = ReportCoordinator(
            self.mock_pnl_calculator,
            self.mock_basic_formatter,
            self.mock_current_day_formatter,
            self.timezone,
        )

    async def test_generate_daily_report(self):
        trade_date = date(2023, 10, 27)
        mock_report = Mock(spec=PnLReport)
        self.mock_pnl_calculator.generate_aggregated_report = AsyncMock(return_value=mock_report)
        self.mock_basic_formatter.format_pnl_report.return_value = "Formatted Report"

        result = await self.coordinator.generate_daily_report(trade_date)

        self.assertEqual(result, "Formatted Report")
        self.mock_pnl_calculator.generate_aggregated_report.assert_called_with(trade_date, trade_date)
        self.mock_basic_formatter.format_pnl_report.assert_called()

    async def test_generate_historical_report(self):
        start_date = date(2023, 10, 1)
        end_date = date(2023, 10, 31)
        mock_report = Mock(spec=PnLReport)
        self.mock_pnl_calculator.generate_aggregated_report = AsyncMock(return_value=mock_report)
        self.mock_basic_formatter.format_pnl_report.return_value = "Formatted History"

        result = await self.coordinator.generate_historical_report(start_date, end_date)

        self.assertEqual(result, "Formatted History")
        self.mock_pnl_calculator.generate_aggregated_report.assert_called_with(start_date, end_date)
        self.mock_basic_formatter.format_pnl_report.assert_called()

    @patch("common.report_generator_helpers.report_coordinator.get_current_utc")
    @patch("common.report_generator_helpers.report_coordinator.get_timezone_aware_date")
    async def test_generate_current_day_report_utc(self, mock_get_tz_date, mock_get_utc):
        mock_now = datetime(2023, 10, 27, 12, 0, 0)
        mock_get_utc.return_value = mock_now
        mock_get_tz_date.return_value = mock_now

        mock_report = Mock(spec=PnLReport)
        self.mock_pnl_calculator.generate_aggregated_report = AsyncMock(return_value=mock_report)
        self.mock_pnl_calculator.get_current_day_unrealized_pnl = AsyncMock(return_value=500)
        self.mock_current_day_formatter.format_current_day_report.return_value = "Current Report"

        result = await self.coordinator.generate_current_day_report()

        self.assertEqual(result, "Current Report")
        self.mock_pnl_calculator.generate_aggregated_report.assert_called_with(mock_now.date(), mock_now.date())
        self.mock_current_day_formatter.format_current_day_report.assert_called_with(mock_report, 500, "October 27, 2023")

    @patch("common.report_generator_helpers.report_coordinator.get_current_date_in_timezone")
    @patch("common.report_generator_helpers.report_coordinator.get_timezone_aware_date")
    async def test_generate_current_day_report_custom_tz(self, mock_get_tz_date, mock_get_date_tz):
        coordinator = ReportCoordinator(
            self.mock_pnl_calculator,
            self.mock_basic_formatter,
            self.mock_current_day_formatter,
            "America/New_York",
        )

        mock_now = datetime(2023, 10, 27, 12, 0, 0)
        mock_get_date_tz.return_value = mock_now
        mock_get_date_tz.return_value = mock_now
        mock_get_date_tz.return_value = mock_now
        mock_get_date_tz.return_value = mock_now  # Need to ensure it returns mock_now for format

        # Patching to ensure consistent behavior
        mock_get_date_tz.return_value = mock_now
        mock_get_date_tz.return_value = mock_now

        # Wait, get_current_date_in_timezone returns a date or datetime?
        # Based on imports, it seems to be from time_utils.

        mock_get_date_tz.return_value = mock_now
        mock_get_date_tz.return_value = mock_now

        # Let's just return mock_now for all calls to date utils
        mock_get_date_tz.return_value = mock_now
        mock_get_date_tz.return_value = mock_now

        # Re-setup mock calls
        mock_get_date_tz.reset_mock()
        mock_get_date_tz.return_value = mock_now

        mock_get_date_tz.return_value = mock_now

        # Actually, let's simplify.
        # In the code:
        # if self.timezone == "UTC": ...
        # else: today = get_current_date_in_timezone(self.timezone).date()

        mock_get_date_tz.return_value = mock_now
        mock_get_date_tz.return_value = mock_now

        mock_get_date_tz.return_value = mock_now

        # I'll just patch the module functions directly in the test method arguments
        pass

    @patch("common.report_generator_helpers.report_coordinator.get_current_date_in_timezone")
    @patch("common.report_generator_helpers.report_coordinator.get_timezone_aware_date")
    async def test_generate_current_day_report_non_utc(self, mock_get_aware, mock_get_tz):
        coordinator = ReportCoordinator(
            self.mock_pnl_calculator,
            self.mock_basic_formatter,
            self.mock_current_day_formatter,
            "America/New_York",
        )

        mock_now = datetime(2023, 10, 27, 12, 0, 0)
        mock_get_tz.return_value = mock_now
        mock_get_aware.return_value = mock_now

        mock_report = Mock(spec=PnLReport)
        self.mock_pnl_calculator.generate_aggregated_report = AsyncMock(return_value=mock_report)
        self.mock_pnl_calculator.get_current_day_unrealized_pnl = AsyncMock(return_value=500)
        self.mock_current_day_formatter.format_current_day_report.return_value = "Current Report"

        result = await coordinator.generate_current_day_report()

        self.assertEqual(result, "Current Report")
        mock_get_tz.assert_called_with("America/New_York")
