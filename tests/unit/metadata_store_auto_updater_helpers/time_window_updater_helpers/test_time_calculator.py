"""Tests for time calculator."""

from __future__ import annotations

from datetime import datetime

from src.common.metadata_store_auto_updater_helpers.time_window_updater_helpers.time_calculator import (
    calculate_time_thresholds,
)


class TestCalculateTimeThresholds:
    """Tests for calculate_time_thresholds function."""

    def test_returns_three_timestamps(self) -> None:
        """Returns tuple of three timestamp strings."""
        current = datetime(2025, 1, 15, 12, 30, 45)

        result = calculate_time_thresholds(current)

        assert len(result) == 3

    def test_hour_ago_is_one_hour_before(self) -> None:
        """First value is one hour before current time."""
        current = datetime(2025, 1, 15, 12, 30, 45)

        hour_ago, _, _ = calculate_time_thresholds(current)

        assert hour_ago == "2025-01-15 11:30:45"

    def test_sixty_five_minutes_ago(self) -> None:
        """Second value is 65 minutes before current time."""
        current = datetime(2025, 1, 15, 12, 30, 45)

        _, sixty_five_ago, _ = calculate_time_thresholds(current)

        assert sixty_five_ago == "2025-01-15 11:25:45"

    def test_sixty_seconds_ago(self) -> None:
        """Third value is 60 seconds before current time."""
        current = datetime(2025, 1, 15, 12, 30, 45)

        _, _, sixty_seconds_ago = calculate_time_thresholds(current)

        assert sixty_seconds_ago == "2025-01-15 12:29:45"

    def test_handles_midnight_boundary(self) -> None:
        """Handles crossing midnight boundary correctly."""
        current = datetime(2025, 1, 15, 0, 30, 0)

        hour_ago, sixty_five_ago, _ = calculate_time_thresholds(current)

        assert hour_ago == "2025-01-14 23:30:00"
        assert sixty_five_ago == "2025-01-14 23:25:00"

    def test_format_is_iso_like(self) -> None:
        """All timestamps follow YYYY-MM-DD HH:MM:SS format."""
        current = datetime(2025, 6, 1, 8, 5, 3)

        hour_ago, sixty_five_ago, sixty_seconds_ago = calculate_time_thresholds(current)

        for ts in [hour_ago, sixty_five_ago, sixty_seconds_ago]:
            datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
