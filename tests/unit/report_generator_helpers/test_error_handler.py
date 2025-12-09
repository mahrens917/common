import unittest
from unittest.mock import AsyncMock, patch

from src.common.report_generator_helpers.error_handler import ReportErrorHandler


class TestReportErrorHandler(unittest.IsolatedAsyncioTestCase):
    async def test_handle_report_error_success(self):
        mock_operation = AsyncMock(return_value="Success")
        result = await ReportErrorHandler.handle_report_error(
            mock_operation, "Error Message", "Log Context"
        )
        self.assertEqual(result, "Success")

    @patch("src.common.report_generator_helpers.error_handler.logger")
    async def test_handle_report_error_failure(self, mock_logger):
        mock_operation = AsyncMock(side_effect=ValueError("Failure"))
        result = await ReportErrorHandler.handle_report_error(
            mock_operation, "Error Message", "Log Context"
        )
        self.assertEqual(result, "❌ Error Message")
        mock_logger.error.assert_called()

    async def test_handle_report_error_unexpected_exception(self):
        mock_operation = AsyncMock(side_effect=RuntimeError("Unexpected"))
        with self.assertRaises(RuntimeError):
            await ReportErrorHandler.handle_report_error(
                mock_operation, "Error Message", "Log Context"
            )
