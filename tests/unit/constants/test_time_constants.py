"""Tests for time constants module."""

from __future__ import annotations


class TestTimeConstants:
    """Tests for time constants."""

    def test_seconds_per_minute_is_sixty(self) -> None:
        """SECONDS_PER_MINUTE should be 60."""
        from common.constants.time import SECONDS_PER_MINUTE

        assert SECONDS_PER_MINUTE == 60

    def test_seconds_per_hour_is_3600(self) -> None:
        """SECONDS_PER_HOUR should be 3600."""
        from common.constants.time import SECONDS_PER_HOUR

        assert SECONDS_PER_HOUR == 3600

    def test_health_check_timeout_is_positive(self) -> None:
        """HEALTH_CHECK_TIMEOUT should be a positive value."""
        from common.constants.time import HEALTH_CHECK_TIMEOUT

        assert HEALTH_CHECK_TIMEOUT > 0
        assert HEALTH_CHECK_TIMEOUT == 300

    def test_time_constants_all_exported(self) -> None:
        """All time constants should be in __all__."""
        from common.constants import time as time_module

        assert "SECONDS_PER_MINUTE" in time_module.__all__
        assert "SECONDS_PER_HOUR" in time_module.__all__
        assert "HEALTH_CHECK_TIMEOUT" in time_module.__all__

    def test_seconds_per_hour_equals_minutes_times_seconds(self) -> None:
        """SECONDS_PER_HOUR should equal SECONDS_PER_MINUTE * 60."""
        from common.constants.time import SECONDS_PER_HOUR, SECONDS_PER_MINUTE

        assert SECONDS_PER_HOUR == SECONDS_PER_MINUTE * 60
