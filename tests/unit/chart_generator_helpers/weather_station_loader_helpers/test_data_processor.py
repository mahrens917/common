"""Tests for chart_generator_helpers.weather_station_loader_helpers.data_processor module."""

import logging
from datetime import datetime, timezone

import pytest

from common.chart_generator.exceptions import InsufficientDataError
from common.chart_generator_helpers.weather_station_loader_helpers.data_processor import (
    process_temperature_data,
)


class TestProcessTemperatureData:
    """Tests for process_temperature_data function."""

    def test_processes_valid_data(self) -> None:
        """Test processes valid temperature data."""
        now = int(datetime.now(tz=timezone.utc).timestamp())
        data = [(now, 72.5), (now + 60, 73.0), (now + 120, 74.5)]

        timestamps, temperatures = process_temperature_data(data, "KMIA")

        assert len(timestamps) == 3
        assert len(temperatures) == 3
        assert temperatures == [72.5, 73.0, 74.5]

    def test_returns_timezone_aware_timestamps(self) -> None:
        """Test returns timezone-aware timestamps."""
        now = int(datetime.now(tz=timezone.utc).timestamp())
        data = [(now, 72.5)]

        timestamps, _ = process_temperature_data(data, "KMIA")

        assert timestamps[0].tzinfo is not None

    def test_skips_invalid_timestamps(self, caplog) -> None:
        """Test skips invalid timestamps with warning."""
        now = int(datetime.now(tz=timezone.utc).timestamp())
        # Use extreme values that will cause OverflowError
        data = [(-999999999999999, 72.5), (now, 73.0)]

        with caplog.at_level(logging.WARNING, logger="src.monitor.chart_generator"):
            timestamps, temperatures = process_temperature_data(data, "KMIA")

            assert len(timestamps) == 1
            assert temperatures == [73.0]
            assert "Skipping invalid timestamp" in caplog.text

    def test_skips_invalid_temperatures(self, caplog) -> None:
        """Test skips invalid temperature values."""
        now = int(datetime.now(tz=timezone.utc).timestamp())
        data = [(now, "invalid"), (now + 60, 73.0)]

        with caplog.at_level(logging.WARNING, logger="src.monitor.chart_generator"):
            timestamps, temperatures = process_temperature_data(data, "KMIA")

            assert len(timestamps) == 1
            assert temperatures == [73.0]
            assert "Skipping invalid temperature data" in caplog.text

    def test_raises_on_empty_data(self) -> None:
        """Test raises InsufficientDataError on empty data."""
        with pytest.raises(InsufficientDataError) as exc_info:
            process_temperature_data([], "KMIA")

        assert "KMIA" in str(exc_info.value)

    def test_raises_on_all_invalid_data(self) -> None:
        """Test raises InsufficientDataError when all data is invalid."""
        data = [(-999999999999999, 72.5)]

        with pytest.raises(InsufficientDataError) as exc_info:
            process_temperature_data(data, "KJFK")

        assert "KJFK" in str(exc_info.value)

    def test_handles_float_temperature_conversion(self) -> None:
        """Test converts temperature to float."""
        now = int(datetime.now(tz=timezone.utc).timestamp())
        data = [(now, 72)]  # Integer temperature

        _, temperatures = process_temperature_data(data, "KMIA")

        assert temperatures == [72.0]
        assert isinstance(temperatures[0], float)

    def test_handles_none_temperature(self, caplog) -> None:
        """Test handles None temperature value."""
        now = int(datetime.now(tz=timezone.utc).timestamp())
        data = [(now, None), (now + 60, 73.0)]

        with caplog.at_level(logging.WARNING, logger="src.monitor.chart_generator"):
            timestamps, temperatures = process_temperature_data(data, "KMIA")

            assert len(timestamps) == 1
            assert temperatures == [73.0]

    def test_preserves_order(self) -> None:
        """Test preserves order of data points."""
        now = int(datetime.now(tz=timezone.utc).timestamp())
        data = [(now, 70.0), (now + 60, 75.0), (now + 120, 72.0)]

        timestamps, temperatures = process_temperature_data(data, "KMIA")

        assert temperatures == [70.0, 75.0, 72.0]
        assert timestamps[0] < timestamps[1] < timestamps[2]

    def test_handles_negative_temperatures(self) -> None:
        """Test handles negative temperature values."""
        now = int(datetime.now(tz=timezone.utc).timestamp())
        data = [(now, -10.5), (now + 60, -5.0)]

        _, temperatures = process_temperature_data(data, "KORD")

        assert temperatures == [-10.5, -5.0]
