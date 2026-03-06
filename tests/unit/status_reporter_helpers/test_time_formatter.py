import pytest

from common.status_reporter_helpers import formatters


class TestTimeFormatter:
    def test_format_wait_duration_seconds(self):
        assert formatters.format_wait_duration(1) == "1 second"
        assert formatters.format_wait_duration(30) == "30 seconds"

    def test_format_wait_duration_minutes(self):
        assert formatters.format_wait_duration(60) == "1 minute"
        assert formatters.format_wait_duration(120) == "2 minutes"
        assert formatters.format_wait_duration(90) == "1m 30s"
        assert formatters.format_wait_duration(3665) == "61m 5s"

    def test_waiting_for_next_scan(self):
        assert formatters.waiting_for_next_scan(60) == "⏳ Waiting 1 minute until next scan"
