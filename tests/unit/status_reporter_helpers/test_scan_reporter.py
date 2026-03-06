from unittest.mock import Mock

import pytest

from common.status_reporter_helpers import formatters
from common.status_reporter_helpers.reporters import ScanReporter


class TestScanReporter:
    @pytest.fixture
    def writer(self):
        return Mock()

    @pytest.fixture
    def reporter(self, writer):
        return ScanReporter(writer)

    def test_scanning_markets(self, reporter, writer):
        reporter.scanning_markets(10)
        writer.write.assert_called_once_with(formatters.scanning_markets(10))

    def test_opportunities_summary(self, reporter, writer):
        reporter.opportunities_summary(5, 2, 1)
        expected_msg = formatters.build_opportunities_summary(5, 2, 1)
        writer.write.assert_called_once_with(expected_msg)

    def test_waiting_for_next_scan(self, reporter, writer):
        reporter.waiting_for_next_scan(60)
        expected_msg = formatters.waiting_for_next_scan(60)
        writer.write.assert_called_once_with(expected_msg)
