"""Tests for chart_generator_helpers.weather_station_loader module."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.chart_generator.exceptions import InsufficientDataError
from common.chart_generator_helpers.weather_station_loader import WeatherStationLoader


class TestWeatherStationLoaderLoadStationTemperatureSeries:
    """Tests for load_station_temperature_series method."""

    @pytest.mark.asyncio
    async def test_loads_temperature_series(self) -> None:
        """Test loads temperature series for a station."""
        now = int(datetime.now(tz=timezone.utc).timestamp())
        temp_data = [(now, 72.5), (now + 60, 73.0), (now + 120, 74.5)]

        with patch.object(WeatherStationLoader, "_create_tracker") as mock_create:
            mock_tracker = MagicMock()
            mock_tracker.initialize = AsyncMock()
            mock_tracker.get_temperature_history = AsyncMock(return_value=temp_data)
            mock_tracker.cleanup = AsyncMock()
            mock_create.return_value = mock_tracker

            loader = WeatherStationLoader()
            result = await loader.load_station_temperature_series("KMIA")

            assert len(result.timestamps) == 3
            assert result.temperatures == [72.5, 73.0, 74.5]
            assert result.current_temperature == 74.5

    @pytest.mark.asyncio
    async def test_raises_on_no_data(self) -> None:
        """Test raises InsufficientDataError on no data."""
        with patch.object(WeatherStationLoader, "_create_tracker") as mock_create:
            mock_tracker = MagicMock()
            mock_tracker.initialize = AsyncMock()
            mock_tracker.get_temperature_history = AsyncMock(return_value=None)
            mock_tracker.cleanup = AsyncMock()
            mock_create.return_value = mock_tracker

            loader = WeatherStationLoader()

            with pytest.raises(InsufficientDataError) as exc_info:
                await loader.load_station_temperature_series("KMIA")

            assert "KMIA" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_raises_on_insufficient_data(self) -> None:
        """Test raises InsufficientDataError on insufficient data."""
        now = int(datetime.now(tz=timezone.utc).timestamp())
        temp_data = [(now, 72.5)]  # Only 1 point

        with patch.object(WeatherStationLoader, "_create_tracker") as mock_create:
            mock_tracker = MagicMock()
            mock_tracker.initialize = AsyncMock()
            mock_tracker.get_temperature_history = AsyncMock(return_value=temp_data)
            mock_tracker.cleanup = AsyncMock()
            mock_create.return_value = mock_tracker

            loader = WeatherStationLoader()

            with pytest.raises(InsufficientDataError) as exc_info:
                await loader.load_station_temperature_series("KJFK")

            assert "Insufficient" in str(exc_info.value)


class TestWeatherStationLoaderEnsureMinimumData:
    """Tests for _ensure_minimum_data method."""

    def test_raises_on_empty_list(self) -> None:
        """Test raises on empty list."""
        loader = WeatherStationLoader()

        with pytest.raises(InsufficientDataError):
            loader._ensure_minimum_data("KMIA", [])

    def test_raises_on_none(self) -> None:
        """Test raises on None."""
        loader = WeatherStationLoader()

        with pytest.raises(InsufficientDataError):
            loader._ensure_minimum_data("KMIA", None)

    def test_raises_on_single_point(self) -> None:
        """Test raises on single data point."""
        loader = WeatherStationLoader()

        with pytest.raises(InsufficientDataError):
            loader._ensure_minimum_data("KMIA", [(123, 72.5)])

    def test_passes_with_two_points(self) -> None:
        """Test passes with two data points."""
        loader = WeatherStationLoader()

        # Should not raise
        loader._ensure_minimum_data("KMIA", [(123, 72.5), (124, 73.0)])


class TestWeatherStationLoaderParseTemperatureSamples:
    """Tests for _parse_temperature_samples method."""

    def test_parses_valid_samples(self) -> None:
        """Test parses valid temperature samples."""
        now = int(datetime.now(tz=timezone.utc).timestamp())
        data = [(now, 72.5), (now + 60, 73.0)]

        loader = WeatherStationLoader()
        timestamps, temperatures = loader._parse_temperature_samples("KMIA", data)

        assert len(timestamps) == 2
        assert temperatures == [72.5, 73.0]

    def test_skips_invalid_timestamps(self, caplog) -> None:
        """Test skips invalid timestamps."""
        now = int(datetime.now(tz=timezone.utc).timestamp())
        data = [(-999999999999999, 72.5), (now, 73.0), (now + 60, 74.0)]

        loader = WeatherStationLoader()
        timestamps, temperatures = loader._parse_temperature_samples("KMIA", data)

        assert len(timestamps) == 2
        assert temperatures == [73.0, 74.0]

    def test_skips_invalid_temperatures(self, caplog) -> None:
        """Test skips invalid temperature values."""
        now = int(datetime.now(tz=timezone.utc).timestamp())
        data = [(now, "invalid"), (now + 60, 73.0), (now + 120, 74.0)]

        loader = WeatherStationLoader()
        timestamps, temperatures = loader._parse_temperature_samples("KMIA", data)

        assert len(timestamps) == 2
        assert temperatures == [73.0, 74.0]

    def test_raises_on_no_valid_data(self) -> None:
        """Test raises when all data is invalid."""
        data = [(-999999999999999, 72.5)]

        loader = WeatherStationLoader()

        with pytest.raises(InsufficientDataError):
            loader._parse_temperature_samples("KMIA", data)


class TestWeatherStationLoaderCoerceTimestamp:
    """Tests for _coerce_timestamp method."""

    def test_coerces_valid_timestamp(self) -> None:
        """Test coerces valid timestamp."""
        now = int(datetime.now(tz=timezone.utc).timestamp())

        loader = WeatherStationLoader()
        result = loader._coerce_timestamp("KMIA", now)

        assert result is not None
        assert result.tzinfo is not None

    def test_returns_none_for_invalid_timestamp(self) -> None:
        """Test returns None for invalid timestamp."""
        loader = WeatherStationLoader()
        result = loader._coerce_timestamp("KMIA", -999999999999999)

        assert result is None


class TestWeatherStationLoaderBuildChartSeries:
    """Tests for _build_chart_series method."""

    def test_sorts_data_by_timestamp(self) -> None:
        """Test sorts data by timestamp."""
        now = datetime.now(tz=timezone.utc)
        t1 = now.replace(minute=10)
        t2 = now.replace(minute=20)
        t3 = now.replace(minute=30)

        # Unsorted input
        timestamps = [t2, t3, t1]
        temperatures = [20.0, 30.0, 10.0]

        loader = WeatherStationLoader()
        result = loader._build_chart_series(timestamps, temperatures)

        # Should be sorted
        assert result.timestamps == [t1, t2, t3]
        assert result.temperatures == [10.0, 20.0, 30.0]

    def test_sets_current_temperature(self) -> None:
        """Test sets current temperature to last value."""
        now = datetime.now(tz=timezone.utc)
        timestamps = [now.replace(minute=10), now.replace(minute=20)]
        temperatures = [72.0, 75.0]

        loader = WeatherStationLoader()
        result = loader._build_chart_series(timestamps, temperatures)

        assert result.current_temperature == 75.0
