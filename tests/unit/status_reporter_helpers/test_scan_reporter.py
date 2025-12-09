from unittest.mock import Mock

import pytest

from src.common.status_reporter_helpers.message_formatter import MessageFormatter
from src.common.status_reporter_helpers.scan_reporter import ScanReporter
from src.common.status_reporter_helpers.summary_builder import SummaryBuilder
from src.common.status_reporter_helpers.time_formatter import TimeFormatter


class TestScanReporter:
    @pytest.fixture
    def writer(self):
        return Mock()

    @pytest.fixture
    def reporter(self, writer):
        return ScanReporter(writer)

    def test_scanning_markets(self, reporter, writer):
        reporter.scanning_markets(10)
        writer.write.assert_called_once_with(MessageFormatter.scanning_markets(10))

    def test_opportunities_summary(self, reporter, writer):
        reporter.opportunities_summary(5, 2, 1)
        expected_msg = SummaryBuilder.build_opportunities_summary(5, 2, 1)
        writer.write.assert_called_once_with(expected_msg)

    def test_waiting_for_next_scan(self, reporter, writer):
        reporter.waiting_for_next_scan(60)
        expected_msg = TimeFormatter.waiting_for_next_scan(60)
        writer.write.assert_called_once_with(expected_msg)
