import unittest
from unittest.mock import Mock

from src.common.pnl_calculator import PnLCalculator
from src.common.report_generator_helpers.coordinator_factory import CoordinatorFactory
from src.common.report_generator_helpers.message_formatter import MessageFormatter
from src.common.report_generator_helpers.report_coordinator import ReportCoordinator
from src.common.report_generator_helpers.summary_report_builder import SummaryReportBuilder
from src.common.report_generator_helpers.unified_report_builder import UnifiedReportBuilder


class TestCoordinatorFactory(unittest.TestCase):
    def test_create_coordinators(self):
        mock_calculator = Mock(spec=PnLCalculator)
        timezone = "UTC"

        (
            message_formatter,
            report_coordinator,
            summary_builder,
            unified_builder,
        ) = CoordinatorFactory.create_coordinators(mock_calculator, timezone)

        self.assertIsInstance(message_formatter, MessageFormatter)
        self.assertIsInstance(report_coordinator, ReportCoordinator)
        self.assertIsInstance(summary_builder, SummaryReportBuilder)
        self.assertIsInstance(unified_builder, UnifiedReportBuilder)

        self.assertEqual(report_coordinator.timezone, timezone)
        self.assertEqual(summary_builder.timezone, timezone)
        self.assertEqual(unified_builder.timezone, timezone)
        self.assertEqual(report_coordinator.pnl_calculator, mock_calculator)
