import pytest

from common.status_reporter_helpers import formatters


class TestMessageFormatter:
    def test_tracking_started(self):
        assert formatters.tracking_started() == "🔍 Tracking..."

    def test_markets_closed(self):
        assert formatters.markets_closed() == "🔒 Markets closed - waiting for next check"

    def test_markets_open(self):
        assert formatters.markets_open() == "✅ Markets open for trading"

    def test_scanning_markets(self):
        assert formatters.scanning_markets(10) == "🔍 Scanning 10 markets for opportunities..."

    def test_initialization_complete(self):
        assert formatters.initialization_complete() == "🚀 Tracker initialized and ready"

    def test_shutdown_complete(self):
        assert formatters.shutdown_complete() == "🛑 Tracker shutdown complete"

    def test_checking_market_hours(self):
        assert formatters.checking_market_hours() == "🕐 Checking market hours..."

    def test_error_occurred(self):
        error = "test error"
        assert formatters.error_occurred(error) == f"❌ Error: {error}"
