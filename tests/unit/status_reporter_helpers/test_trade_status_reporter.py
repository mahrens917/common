from unittest.mock import Mock, patch

import pytest

from common.status_reporter_helpers.trade_status_reporter import TradeStatusReporter


class TestTradeStatusReporter:
    @pytest.fixture
    def writer(self):
        return Mock()

    @pytest.fixture
    def reporter(self, writer):
        return TradeStatusReporter(writer)

    def test_trade_opportunity_found(self, reporter, writer):
        with patch(
            "common.status_reporter_helpers.trade_status_reporter.OpportunityReporter"
        ) as MockOpp:
            MockOpp.format_opportunity.return_value = "Opp Msg"
            reporter.trade_opportunity_found("T", "A", "S", 1, "R", "W")
            writer.write.assert_called_once_with("Opp Msg")
            MockOpp.format_opportunity.assert_called_once_with("T", "A", "S", 1, "R", "W")

    def test_trade_executed(self, reporter, writer):
        with patch(
            "common.status_reporter_helpers.trade_status_reporter.TradeReporter"
        ) as MockTrade:
            MockTrade.format_trade_executed.return_value = "Exec Msg"
            reporter.trade_executed("T", "A", "S", 1, "ID")
            writer.write.assert_called_once_with("Exec Msg")
            MockTrade.format_trade_executed.assert_called_once_with("T", "A", "S", 1, "ID")

    def test_trade_failed(self, reporter, writer):
        with patch(
            "common.status_reporter_helpers.trade_status_reporter.TradeReporter"
        ) as MockTrade:
            MockTrade.format_trade_failed.return_value = "Fail Msg"
            reporter.trade_failed("T", "R")
            writer.write.assert_called_once_with("Fail Msg")
            MockTrade.format_trade_failed.assert_called_once_with("T", "R")

    def test_insufficient_balance(self, reporter, writer):
        with patch(
            "common.status_reporter_helpers.trade_status_reporter.TradeReporter"
        ) as MockTrade:
            MockTrade.format_insufficient_balance.return_value = "Bal Msg"
            reporter.insufficient_balance("T", 10, 5)
            writer.write.assert_called_once_with("Bal Msg")
            MockTrade.format_insufficient_balance.assert_called_once_with("T", 10, 5)

    def test_balance_updated(self, reporter, writer):
        with patch(
            "common.status_reporter_helpers.trade_status_reporter.TradeReporter"
        ) as MockTrade:
            MockTrade.format_balance_updated.return_value = "Upd Msg"
            reporter.balance_updated(10, 20)
            writer.write.assert_called_once_with("Upd Msg")
            MockTrade.format_balance_updated.assert_called_once_with(10, 20)
