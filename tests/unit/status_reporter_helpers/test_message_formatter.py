import pytest

from src.common.status_reporter_helpers.message_formatter import MessageFormatter


class TestMessageFormatter:
    def test_tracking_started(self):
        assert MessageFormatter.tracking_started() == "🔍 Tracking..."

    def test_markets_closed(self):
        assert MessageFormatter.markets_closed() == "🔒 Markets closed - waiting for next check"

    def test_markets_open(self):
        assert MessageFormatter.markets_open() == "✅ Markets open for trading"

    def test_scanning_markets(self):
        assert (
            MessageFormatter.scanning_markets(10) == "🔍 Scanning 10 markets for opportunities..."
        )

    def test_initialization_complete(self):
        assert MessageFormatter.initialization_complete() == "🚀 Tracker initialized and ready"

    def test_shutdown_complete(self):
        assert MessageFormatter.shutdown_complete() == "🛑 Tracker shutdown complete"

    def test_checking_market_hours(self):
        assert MessageFormatter.checking_market_hours() == "🕐 Checking market hours..."

    def test_error_occurred(self):
        error = "test error"
        assert MessageFormatter.error_occurred(error) == f"❌ Error: {error}"
