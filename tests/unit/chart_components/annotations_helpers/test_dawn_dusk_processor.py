"""Tests for dawn_dusk_processor module."""

from datetime import datetime, timezone

from common.chart_components.annotations_helpers.dawn_dusk_processor import (
    process_dawn_dusk_periods,
)


class TestProcessDawnDuskPeriods:
    """Tests for process_dawn_dusk_periods function."""

    def test_empty_periods(self) -> None:
        """Test processing empty list of periods."""
        all_dawns, all_dusks = process_dawn_dusk_periods([])
        assert all_dawns == []
        assert all_dusks == []

    def test_single_period_naive_datetimes(self) -> None:
        """Test processing single period with naive datetimes."""
        dawn = datetime(2024, 6, 15, 6, 0)
        dusk = datetime(2024, 6, 15, 20, 0)
        all_dawns, all_dusks = process_dawn_dusk_periods([(dawn, dusk)])
        assert len(all_dawns) == 1
        assert len(all_dusks) == 1
        assert all_dawns[0][1] == dawn
        assert all_dusks[0][1] == dusk

    def test_single_period_aware_datetimes(self) -> None:
        """Test processing single period with timezone-aware datetimes."""
        dawn = datetime(2024, 6, 15, 6, 0, tzinfo=timezone.utc)
        dusk = datetime(2024, 6, 15, 20, 0, tzinfo=timezone.utc)
        all_dawns, all_dusks = process_dawn_dusk_periods([(dawn, dusk)])
        assert len(all_dawns) == 1
        assert len(all_dusks) == 1
        assert all_dawns[0][1].tzinfo is None
        assert all_dusks[0][1].tzinfo is None

    def test_multiple_periods_sorted(self) -> None:
        """Test that multiple periods are sorted by numeric date."""
        periods = [
            (datetime(2024, 6, 17, 6, 0), datetime(2024, 6, 17, 20, 0)),
            (datetime(2024, 6, 15, 6, 0), datetime(2024, 6, 15, 20, 0)),
            (datetime(2024, 6, 16, 6, 0), datetime(2024, 6, 16, 20, 0)),
        ]
        all_dawns, all_dusks = process_dawn_dusk_periods(periods)
        assert len(all_dawns) == 3
        assert len(all_dusks) == 3
        assert all_dawns[0][1].day == 15
        assert all_dawns[1][1].day == 16
        assert all_dawns[2][1].day == 17

    def test_numeric_values_are_floats(self) -> None:
        """Test that numeric date values are floats."""
        dawn = datetime(2024, 6, 15, 6, 0)
        dusk = datetime(2024, 6, 15, 20, 0)
        all_dawns, all_dusks = process_dawn_dusk_periods([(dawn, dusk)])
        assert isinstance(all_dawns[0][0], float)
        assert isinstance(all_dusks[0][0], float)
