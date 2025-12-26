"""Tests for chart_components.time_conversions module."""

from datetime import datetime, timezone
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from common.chart_components.time_conversions import (
    LocalizedTimestamps,
    build_axis_timestamps,
    ensure_naive_timestamps,
    localize_temperature_timestamps,
)


class TestLocalizedTimestamps:
    """Tests for LocalizedTimestamps dataclass."""

    def test_frozen(self) -> None:
        """Test dataclass is frozen."""
        ts = LocalizedTimestamps(
            timestamps=[datetime(2025, 1, 15, 12, 0, 0)],
            timezone=timezone.utc,
        )
        with pytest.raises(AttributeError):
            ts.timestamps = []

    def test_creation(self) -> None:
        """Test dataclass creation."""
        now = datetime(2025, 1, 15, 12, 0, 0)
        ts = LocalizedTimestamps(
            timestamps=[now],
            timezone=timezone.utc,
        )
        assert ts.timestamps == [now]
        assert ts.timezone == timezone.utc


class TestEnsureNaiveTimestamps:
    """Tests for ensure_naive_timestamps function."""

    def test_strips_timezone(self) -> None:
        """Test strips timezone from aware timestamps."""
        aware = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        result = ensure_naive_timestamps([aware])

        assert len(result) == 1
        assert result[0].tzinfo is None
        assert result[0].year == 2025

    def test_keeps_naive(self) -> None:
        """Test keeps naive timestamps as is."""
        naive = datetime(2025, 1, 15, 12, 0, 0)
        result = ensure_naive_timestamps([naive])

        assert len(result) == 1
        assert result[0].tzinfo is None

    def test_mixed_timestamps(self) -> None:
        """Test handles mixed aware and naive."""
        aware = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        naive = datetime(2025, 1, 15, 18, 0, 0)
        result = ensure_naive_timestamps([aware, naive])

        assert len(result) == 2
        assert all(ts.tzinfo is None for ts in result)

    def test_empty_list(self) -> None:
        """Test handles empty list."""
        result = ensure_naive_timestamps([])
        assert result == []


class TestBuildAxisTimestamps:
    """Tests for build_axis_timestamps function."""

    def test_without_predictions(self) -> None:
        """Test returns timestamps when no predictions."""
        timestamps = [datetime(2025, 1, 15, 12, 0, 0)]
        result = build_axis_timestamps(timestamps, None)

        assert result == timestamps

    def test_with_predictions(self) -> None:
        """Test combines and sorts with predictions."""
        ts1 = datetime(2025, 1, 15, 12, 0, 0)
        ts2 = datetime(2025, 1, 15, 6, 0, 0)
        result = build_axis_timestamps([ts1], [ts2])

        assert len(result) == 2
        assert result[0] == ts2
        assert result[1] == ts1

    def test_empty_predictions(self) -> None:
        """Test handles empty predictions list."""
        timestamps = [datetime(2025, 1, 15, 12, 0, 0)]
        result = build_axis_timestamps(timestamps, [])

        assert result == timestamps


class TestLocalizeTemperatureTimestamps:
    """Tests for localize_temperature_timestamps function."""

    def test_localizes_to_station_timezone(self) -> None:
        """Test localizes to station timezone."""
        utc_naive = datetime(2025, 1, 15, 12, 0, 0)
        coordinates = (40.7128, -74.0060)

        with patch(
            "common.chart_components.time_conversions.get_timezone_from_coordinates",
            return_value="America/New_York",
        ):
            result = localize_temperature_timestamps([utc_naive], coordinates)

        assert len(result.timestamps) == 1
        assert result.timestamps[0].tzinfo is None
        assert isinstance(result.timezone, ZoneInfo)

    def test_multiple_timestamps(self) -> None:
        """Test handles multiple timestamps."""
        ts1 = datetime(2025, 1, 15, 12, 0, 0)
        ts2 = datetime(2025, 1, 15, 18, 0, 0)
        coordinates = (34.0522, -118.2437)

        with patch(
            "common.chart_components.time_conversions.get_timezone_from_coordinates",
            return_value="America/Los_Angeles",
        ):
            result = localize_temperature_timestamps([ts1, ts2], coordinates)

        assert len(result.timestamps) == 2

    def test_returns_naive_timestamps(self) -> None:
        """Test returned timestamps are naive."""
        utc_naive = datetime(2025, 1, 15, 12, 0, 0)
        coordinates = (51.5074, -0.1278)

        with patch(
            "common.chart_components.time_conversions.get_timezone_from_coordinates",
            return_value="Europe/London",
        ):
            result = localize_temperature_timestamps([utc_naive], coordinates)

        assert all(ts.tzinfo is None for ts in result.timestamps)
