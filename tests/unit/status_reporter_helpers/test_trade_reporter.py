import pytest

from common.status_reporter_helpers import formatters


class TestTradeReporter:
    def test_format_trade_executed(self):
        result = formatters.format_trade_executed("TICKER", "BUY", "YES", 50, "123")
        assert "✅ Trade executed: BUY YES TICKER @ $0.50 (Order: 123)" in result

    def test_format_trade_failed(self):
        result = formatters.format_trade_failed("TICKER", "Reason")
        assert "❌ Trade failed for TICKER: Reason" in result

    def test_format_insufficient_balance(self):
        result = formatters.format_insufficient_balance("TICKER", 100, 50)
        assert "💸 Insufficient balance for TICKER: need $1.00, have $0.50" in result

    def test_format_balance_updated_positive(self):
        result = formatters.format_balance_updated(100, 200)
        assert "💰 Balance updated: $1.00 → $2.00 (+$1.00)" in result

    def test_format_balance_updated_negative(self):
        result = formatters.format_balance_updated(200, 100)
        assert "💰 Balance updated: $2.00 → $1.00 ($-1.00)" in result
