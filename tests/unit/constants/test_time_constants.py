"""Tests for time constants."""

from __future__ import annotations

from common.constants import (
    HEALTH_CHECK_TIMEOUT,
    SECONDS_PER_HOUR,
    SECONDS_PER_MINUTE,
)


class TestTimeConstants:
    """Tests for time constants."""

    def test_seconds_per_minute_is_sixty(self) -> None:
        assert SECONDS_PER_MINUTE == 60

    def test_seconds_per_hour_is_3600(self) -> None:
        assert SECONDS_PER_HOUR == 3600

    def test_health_check_timeout_is_positive(self) -> None:
        assert HEALTH_CHECK_TIMEOUT > 0
        assert HEALTH_CHECK_TIMEOUT == 300

    def test_seconds_per_hour_equals_minutes_times_seconds(self) -> None:
        assert SECONDS_PER_HOUR == SECONDS_PER_MINUTE * 60
