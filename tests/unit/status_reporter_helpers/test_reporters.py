from unittest.mock import Mock

import pytest

from src.common.status_reporter_helpers.base_reporter import WriterBackedReporter
from src.common.status_reporter_helpers.lifecycle_reporter import LifecycleReporter
from src.common.status_reporter_helpers.market_reporter import MarketReporter
from src.common.status_reporter_helpers.message_formatter import MessageFormatter


class TestWriterBackedReporter:
    def test_init(self):
        writer = Mock()
        reporter = WriterBackedReporter(writer)
        assert reporter._writer == writer


class TestLifecycleReporter:
    @pytest.fixture
    def writer(self):
        return Mock()

    @pytest.fixture
    def reporter(self, writer):
        return LifecycleReporter(writer)

    def test_error_occurred(self, reporter, writer):
        msg = "Something went wrong"
        reporter.error_occurred(msg)
        writer.write.assert_called_once_with(MessageFormatter.error_occurred(msg))

    def test_initialization_complete(self, reporter, writer):
        reporter.initialization_complete()
        writer.write.assert_called_once_with(MessageFormatter.initialization_complete())

    def test_shutdown_complete(self, reporter, writer):
        reporter.shutdown_complete()
        writer.write.assert_called_once_with(MessageFormatter.shutdown_complete())


class TestMarketReporter:
    @pytest.fixture
    def writer(self):
        return Mock()

    @pytest.fixture
    def reporter(self, writer):
        return MarketReporter(writer)

    def test_tracking_started(self, reporter, writer):
        reporter.tracking_started()
        writer.write.assert_called_once_with(MessageFormatter.tracking_started())

    def test_markets_closed(self, reporter, writer):
        reporter.markets_closed()
        writer.write.assert_called_once_with(MessageFormatter.markets_closed())

    def test_markets_open(self, reporter, writer):
        reporter.markets_open()
        writer.write.assert_called_once_with(MessageFormatter.markets_open())

    def test_checking_market_hours(self, reporter, writer):
        reporter.checking_market_hours()
        writer.write.assert_called_once_with(MessageFormatter.checking_market_hours())
