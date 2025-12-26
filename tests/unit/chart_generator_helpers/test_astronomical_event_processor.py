"""Tests for chart_generator_helpers.astronomical_event_processor module."""

from datetime import datetime, timezone
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest

from common.chart_generator_helpers.astronomical_event_processor import (
    AstronomicalEventProcessor,
)
from common.chart_generator_helpers.config import AstronomicalEventData


class TestAstronomicalEventProcessor:
    """Tests for AstronomicalEventProcessor class."""

    def _create_event_data(
        self,
        current_date: datetime,
        start_date: datetime,
        end_date: datetime,
        local_tz=None,
    ) -> AstronomicalEventData:
        """Create event data with mocked calculators."""
        return AstronomicalEventData(
            current_date=current_date,
            latitude=40.7128,
            longitude=-74.0060,
            start_date=start_date,
            end_date=end_date,
            local_tz=local_tz,
            vertical_lines=[],
            dawn_dusk_periods=[],
            calculate_solar_noon_utc=MagicMock(
                return_value=current_date.replace(hour=17, minute=0)
            ),
            calculate_local_midnight_utc=MagicMock(
                return_value=current_date.replace(hour=5, minute=0)
            ),
            calculate_dawn_utc=MagicMock(
                return_value=current_date.replace(hour=12, minute=0)
            ),
            calculate_dusk_utc=MagicMock(
                return_value=current_date.replace(hour=22, minute=0)
            ),
        )

    def test_process_day_adds_solar_noon(self) -> None:
        """Test adds solar noon to vertical lines."""
        processor = AstronomicalEventProcessor()
        current = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        data = self._create_event_data(
            current_date=current,
            start_date=current,
            end_date=current.replace(hour=23, minute=59),
        )

        processor.process_day_astronomical_events(data=data)

        solar_noon_lines = [line for line in data.vertical_lines if line[2] == "Solar Noon"]
        assert len(solar_noon_lines) == 1

    def test_process_day_adds_midnight(self) -> None:
        """Test adds local midnight to vertical lines."""
        processor = AstronomicalEventProcessor()
        current = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        data = self._create_event_data(
            current_date=current,
            start_date=current,
            end_date=current.replace(hour=23, minute=59),
        )

        processor.process_day_astronomical_events(data=data)

        midnight_lines = [line for line in data.vertical_lines if line[2] == "Local Midnight"]
        assert len(midnight_lines) == 1

    def test_process_day_adds_dawn(self) -> None:
        """Test adds dawn to vertical lines."""
        processor = AstronomicalEventProcessor()
        current = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        data = self._create_event_data(
            current_date=current,
            start_date=current,
            end_date=current.replace(hour=23, minute=59),
        )

        processor.process_day_astronomical_events(data=data)

        dawn_lines = [line for line in data.vertical_lines if line[2] == "Dawn"]
        assert len(dawn_lines) == 1

    def test_process_day_adds_dusk(self) -> None:
        """Test adds dusk to vertical lines."""
        processor = AstronomicalEventProcessor()
        current = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        data = self._create_event_data(
            current_date=current,
            start_date=current,
            end_date=current.replace(hour=23, minute=59),
        )

        processor.process_day_astronomical_events(data=data)

        dusk_lines = [line for line in data.vertical_lines if line[2] == "Dusk"]
        assert len(dusk_lines) == 1

    def test_process_day_adds_dawn_dusk_period(self) -> None:
        """Test adds dawn/dusk period."""
        processor = AstronomicalEventProcessor()
        current = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        data = self._create_event_data(
            current_date=current,
            start_date=current,
            end_date=current.replace(hour=23, minute=59),
        )

        processor.process_day_astronomical_events(data=data)

        assert len(data.dawn_dusk_periods) == 1


class TestAddDawnDuskPeriod:
    """Tests for _add_dawn_dusk_period method."""

    def test_with_local_timezone(self) -> None:
        """Test adds period with timezone conversion."""
        processor = AstronomicalEventProcessor()
        dawn = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        dusk = datetime(2025, 1, 15, 22, 0, 0, tzinfo=timezone.utc)
        local_tz = ZoneInfo("America/New_York")
        periods = []

        processor._add_dawn_dusk_period(dawn, dusk, local_tz, periods)

        assert len(periods) == 1
        assert periods[0][0].tzinfo is None
        assert periods[0][1].tzinfo is None

    def test_without_local_timezone(self) -> None:
        """Test adds period without timezone conversion."""
        processor = AstronomicalEventProcessor()
        dawn = datetime(2025, 1, 15, 12, 0, 0)
        dusk = datetime(2025, 1, 15, 22, 0, 0)
        periods = []

        processor._add_dawn_dusk_period(dawn, dusk, None, periods)

        assert len(periods) == 1
        assert periods[0] == (dawn, dusk)
