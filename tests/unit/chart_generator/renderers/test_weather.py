"""Tests for chart_generator.renderers.weather module."""

from datetime import datetime, timezone
from typing import List, Tuple
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from common.chart_generator.contexts import AstronomicalFeatures, WeatherChartSeries
from common.chart_generator.renderers.weather import (
    _COORDINATE_TUPLE_LENGTH,
    WeatherChartRendererMixin,
)

# Test constants (data_guard requirement)
TEST_STATION_ICAO = "KJFK"
TEST_STATION_NAME = "John F. Kennedy International Airport"
TEST_CITY_NAME = "New York"
TEST_CURRENT_TEMP = 65.5
TEST_LATITUDE = 40.6413
TEST_LONGITUDE = -73.7781
TEST_CHART_PATH = "/tmp/test_chart.png"
TEST_STRIKE_TEMP_1 = 60.0
TEST_STRIKE_TEMP_2 = 70.0
TEST_LINE_COLOR = "#2E5BBA"


@pytest.fixture
def mock_renderer():
    """Create a mock WeatherChartRendererMixin instance."""
    renderer = WeatherChartRendererMixin()
    renderer._generate_unified_chart = AsyncMock(return_value=TEST_CHART_PATH)
    renderer._get_kalshi_strikes_for_station = AsyncMock(return_value=[])
    return renderer


@pytest.fixture
def test_timestamps():
    """Create test timestamps."""
    return [
        datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
        datetime(2025, 1, 1, 14, 0, tzinfo=timezone.utc),
    ]


@pytest.fixture
def test_temperatures():
    """Create test temperatures."""
    return [62.0, 64.0, TEST_CURRENT_TEMP]


@pytest.fixture
def test_series(test_timestamps, test_temperatures):
    """Create a test WeatherChartSeries."""
    return WeatherChartSeries(
        timestamps=test_timestamps,
        temperatures=test_temperatures,
        current_temperature=TEST_CURRENT_TEMP,
    )


@pytest.fixture
def test_coordinates():
    """Create test station coordinates."""
    return (TEST_LATITUDE, TEST_LONGITUDE)


@pytest.fixture
def test_astronomical_features(test_timestamps):
    """Create test astronomical features."""
    return AstronomicalFeatures(
        vertical_lines=[
            (test_timestamps[0], "sunrise", "orange"),
            (test_timestamps[2], "sunset", "red"),
        ],
        dawn_dusk_periods=[
            (test_timestamps[0], test_timestamps[1]),
        ],
    )


class TestConstant:
    """Tests for module-level constants."""

    def test_coordinate_tuple_length(self) -> None:
        """Test that _COORDINATE_TUPLE_LENGTH is set correctly."""
        assert _COORDINATE_TUPLE_LENGTH == 2


class TestSanitizeStationCoordinates:
    """Tests for _sanitize_station_coordinates method."""

    def test_valid_coordinates(self, mock_renderer, test_coordinates) -> None:
        """Test sanitizing valid coordinates."""
        result = mock_renderer._sanitize_station_coordinates(TEST_STATION_ICAO, test_coordinates)
        assert result == test_coordinates
        assert isinstance(result[0], float)
        assert isinstance(result[1], float)

    def test_none_coordinates(self, mock_renderer) -> None:
        """Test sanitizing None coordinates."""
        result = mock_renderer._sanitize_station_coordinates(TEST_STATION_ICAO, None)
        assert result is None

    def test_empty_tuple(self, mock_renderer) -> None:
        """Test sanitizing empty tuple."""
        result = mock_renderer._sanitize_station_coordinates(TEST_STATION_ICAO, ())
        assert result is None

    def test_single_element_tuple(self, mock_renderer) -> None:
        """Test sanitizing tuple with single element."""
        result = mock_renderer._sanitize_station_coordinates(TEST_STATION_ICAO, (TEST_LATITUDE,))
        assert result is None

    def test_three_element_tuple(self, mock_renderer) -> None:
        """Test sanitizing tuple with three elements."""
        result = mock_renderer._sanitize_station_coordinates(TEST_STATION_ICAO, (TEST_LATITUDE, TEST_LONGITUDE, 100.0))
        assert result is None

    def test_invalid_type_in_tuple(self, mock_renderer) -> None:
        """Test sanitizing tuple with invalid types."""
        result = mock_renderer._sanitize_station_coordinates(TEST_STATION_ICAO, ("invalid", TEST_LONGITUDE))
        assert result is None

    def test_non_numeric_coordinates(self, mock_renderer) -> None:
        """Test sanitizing tuple with non-numeric values."""
        result = mock_renderer._sanitize_station_coordinates(TEST_STATION_ICAO, ("abc", "def"))
        assert result is None

    def test_integer_coordinates(self, mock_renderer) -> None:
        """Test sanitizing coordinates with integers."""
        result = mock_renderer._sanitize_station_coordinates(TEST_STATION_ICAO, (40, -73))
        assert result == (40.0, -73.0)
        assert isinstance(result[0], float)
        assert isinstance(result[1], float)

    def test_string_numeric_coordinates(self, mock_renderer) -> None:
        """Test sanitizing coordinates with string numbers."""
        result = mock_renderer._sanitize_station_coordinates(TEST_STATION_ICAO, ("40.5", "-73.5"))
        assert result == (40.5, -73.5)

    def test_none_in_coordinates(self, mock_renderer) -> None:
        """Test sanitizing coordinates with None values."""
        result = mock_renderer._sanitize_station_coordinates(TEST_STATION_ICAO, (None, TEST_LONGITUDE))
        assert result is None


class TestFormatWeatherChartTitle:
    """Tests for _format_weather_chart_title method."""

    def test_format_title(self, mock_renderer, test_series) -> None:
        """Test formatting weather chart title."""
        result = mock_renderer._format_weather_chart_title(TEST_STATION_NAME, TEST_STATION_ICAO, test_series)
        assert result == f"{TEST_STATION_NAME} ({TEST_STATION_ICAO}) - {TEST_CURRENT_TEMP:.1f}°F"

    def test_format_title_with_different_temp(self, mock_renderer, test_timestamps, test_temperatures) -> None:
        """Test formatting title with different temperature."""
        series = WeatherChartSeries(
            timestamps=test_timestamps,
            temperatures=test_temperatures,
            current_temperature=72.3,
        )
        result = mock_renderer._format_weather_chart_title(TEST_STATION_NAME, TEST_STATION_ICAO, series)
        assert result == f"{TEST_STATION_NAME} ({TEST_STATION_ICAO}) - 72.3°F"

    def test_format_title_negative_temp(self, mock_renderer, test_timestamps, test_temperatures) -> None:
        """Test formatting title with negative temperature."""
        series = WeatherChartSeries(
            timestamps=test_timestamps,
            temperatures=test_temperatures,
            current_temperature=-5.2,
        )
        result = mock_renderer._format_weather_chart_title(TEST_STATION_NAME, TEST_STATION_ICAO, series)
        assert result == f"{TEST_STATION_NAME} ({TEST_STATION_ICAO}) - -5.2°F"


class TestLoadKalshiStrikesWithLogging:
    """Tests for _load_kalshi_strikes_with_logging method."""

    @pytest.mark.asyncio
    async def test_successful_strikes_found(self, mock_renderer) -> None:
        """Test successfully loading Kalshi strikes."""
        strikes = [TEST_STRIKE_TEMP_1, TEST_STRIKE_TEMP_2]
        mock_renderer._get_kalshi_strikes_for_station = AsyncMock(return_value=strikes)

        result = await mock_renderer._load_kalshi_strikes_with_logging(TEST_STATION_ICAO)
        assert result == strikes
        mock_renderer._get_kalshi_strikes_for_station.assert_awaited_once_with(TEST_STATION_ICAO)

    @pytest.mark.asyncio
    async def test_no_strikes_found(self, mock_renderer) -> None:
        """Test loading when no Kalshi strikes found."""
        mock_renderer._get_kalshi_strikes_for_station = AsyncMock(return_value=[])

        result = await mock_renderer._load_kalshi_strikes_with_logging(TEST_STATION_ICAO)
        assert result == []
        mock_renderer._get_kalshi_strikes_for_station.assert_awaited_once_with(TEST_STATION_ICAO)

    @pytest.mark.asyncio
    async def test_runtime_error_no_strikes_available(self, mock_renderer) -> None:
        """Test handling RuntimeError with 'No Kalshi strikes available' message."""
        error = RuntimeError("No Kalshi strikes available for this station")
        mock_renderer._get_kalshi_strikes_for_station = AsyncMock(side_effect=error)

        result = await mock_renderer._load_kalshi_strikes_with_logging(TEST_STATION_ICAO)
        assert result == []
        mock_renderer._get_kalshi_strikes_for_station.assert_awaited_once_with(TEST_STATION_ICAO)

    @pytest.mark.asyncio
    async def test_runtime_error_other_message(self, mock_renderer) -> None:
        """Test handling RuntimeError with other message raises."""
        error = RuntimeError("Different error message")
        mock_renderer._get_kalshi_strikes_for_station = AsyncMock(side_effect=error)

        with pytest.raises(RuntimeError, match="Different error message"):
            await mock_renderer._load_kalshi_strikes_with_logging(TEST_STATION_ICAO)
        mock_renderer._get_kalshi_strikes_for_station.assert_awaited_once_with(TEST_STATION_ICAO)

    @pytest.mark.asyncio
    async def test_value_error_raises(self, mock_renderer) -> None:
        """Test that ValueError is logged and re-raised."""
        error = ValueError("Invalid value")
        mock_renderer._get_kalshi_strikes_for_station = AsyncMock(side_effect=error)

        with pytest.raises(ValueError, match="Invalid value"):
            await mock_renderer._load_kalshi_strikes_with_logging(TEST_STATION_ICAO)
        mock_renderer._get_kalshi_strikes_for_station.assert_awaited_once_with(TEST_STATION_ICAO)

    @pytest.mark.asyncio
    async def test_os_error_raises(self, mock_renderer) -> None:
        """Test that OSError is logged and re-raised."""
        error = OSError("OS error")
        mock_renderer._get_kalshi_strikes_for_station = AsyncMock(side_effect=error)

        with pytest.raises(OSError, match="OS error"):
            await mock_renderer._load_kalshi_strikes_with_logging(TEST_STATION_ICAO)
        mock_renderer._get_kalshi_strikes_for_station.assert_awaited_once_with(TEST_STATION_ICAO)


class TestGetKalshiStrikesForStation:
    """Tests for _get_kalshi_strikes_for_station method."""

    @pytest.mark.asyncio
    async def test_not_implemented(self, mock_renderer) -> None:
        """Test that the stub raises NotImplementedError."""
        # Reset the mock to use the actual implementation
        del mock_renderer._get_kalshi_strikes_for_station

        with pytest.raises(NotImplementedError):
            await WeatherChartRendererMixin._get_kalshi_strikes_for_station(mock_renderer, TEST_STATION_ICAO)


class TestCreateWeatherChart:
    """Tests for _create_weather_chart method."""

    @pytest.mark.asyncio
    async def test_create_chart_with_valid_coordinates(
        self, mock_renderer, test_series, test_coordinates, test_astronomical_features
    ) -> None:
        """Test creating weather chart with valid coordinates."""
        mock_loader = AsyncMock()
        mock_loader.load_station_temperature_series = AsyncMock(return_value=test_series)

        mock_calculator = Mock()
        mock_calculator.compute_astronomical_features = Mock(return_value=test_astronomical_features)

        mock_renderer._get_kalshi_strikes_for_station = AsyncMock(return_value=[])

        with (
            patch("common.chart_generator.renderers.weather.WeatherStationLoader", return_value=mock_loader),
            patch(
                "common.chart_generator.renderers.weather.AstronomicalCalculator",
                return_value=mock_calculator,
            ),
        ):
            result = await mock_renderer._create_weather_chart(TEST_STATION_ICAO, TEST_STATION_NAME, TEST_CITY_NAME, test_coordinates)

        assert result == TEST_CHART_PATH
        mock_loader.load_station_temperature_series.assert_awaited_once_with(TEST_STATION_ICAO)
        mock_calculator.compute_astronomical_features.assert_called_once_with(TEST_STATION_ICAO, test_coordinates, test_series.timestamps)
        mock_renderer._generate_unified_chart.assert_awaited_once()

        # Verify the call arguments
        call_kwargs = mock_renderer._generate_unified_chart.call_args.kwargs
        assert call_kwargs["timestamps"] == test_series.timestamps
        assert call_kwargs["values"] == test_series.temperatures
        assert call_kwargs["chart_title"] == f"{TEST_STATION_NAME} ({TEST_STATION_ICAO}) - {TEST_CURRENT_TEMP:.1f}°F"
        assert call_kwargs["y_label"] == ""
        assert call_kwargs["is_temperature_chart"] is True
        assert call_kwargs["vertical_lines"] == test_astronomical_features.vertical_lines
        assert call_kwargs["dawn_dusk_periods"] == test_astronomical_features.dawn_dusk_periods
        assert call_kwargs["station_coordinates"] == test_coordinates
        assert call_kwargs["line_color"] == TEST_LINE_COLOR
        assert call_kwargs["kalshi_strikes"] == []
        assert call_kwargs["station_icao"] == TEST_STATION_ICAO

    @pytest.mark.asyncio
    async def test_create_chart_with_none_coordinates(self, mock_renderer, test_series, test_astronomical_features) -> None:
        """Test creating weather chart with None coordinates."""
        mock_loader = AsyncMock()
        mock_loader.load_station_temperature_series = AsyncMock(return_value=test_series)

        mock_calculator = Mock()
        mock_calculator.compute_astronomical_features = Mock(return_value=test_astronomical_features)

        mock_renderer._get_kalshi_strikes_for_station = AsyncMock(return_value=[])

        with (
            patch("common.chart_generator.renderers.weather.WeatherStationLoader", return_value=mock_loader),
            patch(
                "common.chart_generator.renderers.weather.AstronomicalCalculator",
                return_value=mock_calculator,
            ),
        ):
            result = await mock_renderer._create_weather_chart(TEST_STATION_ICAO, TEST_STATION_NAME, TEST_CITY_NAME, None)

        assert result == TEST_CHART_PATH
        mock_renderer._generate_unified_chart.assert_awaited_once()

        # Verify sanitized coordinates are None
        call_kwargs = mock_renderer._generate_unified_chart.call_args.kwargs
        assert call_kwargs["station_coordinates"] is None

    @pytest.mark.asyncio
    async def test_create_chart_with_kalshi_strikes(self, mock_renderer, test_series, test_coordinates, test_astronomical_features) -> None:
        """Test creating weather chart with Kalshi strikes."""
        mock_loader = AsyncMock()
        mock_loader.load_station_temperature_series = AsyncMock(return_value=test_series)

        mock_calculator = Mock()
        mock_calculator.compute_astronomical_features = Mock(return_value=test_astronomical_features)

        strikes = [TEST_STRIKE_TEMP_1, TEST_STRIKE_TEMP_2]
        mock_renderer._get_kalshi_strikes_for_station = AsyncMock(return_value=strikes)

        with (
            patch("common.chart_generator.renderers.weather.WeatherStationLoader", return_value=mock_loader),
            patch(
                "common.chart_generator.renderers.weather.AstronomicalCalculator",
                return_value=mock_calculator,
            ),
        ):
            result = await mock_renderer._create_weather_chart(TEST_STATION_ICAO, TEST_STATION_NAME, TEST_CITY_NAME, test_coordinates)

        assert result == TEST_CHART_PATH

        # Verify strikes are passed
        call_kwargs = mock_renderer._generate_unified_chart.call_args.kwargs
        assert call_kwargs["kalshi_strikes"] == strikes

    @pytest.mark.asyncio
    async def test_create_chart_with_invalid_coordinates(self, mock_renderer, test_series, test_astronomical_features) -> None:
        """Test creating weather chart with invalid coordinates."""
        mock_loader = AsyncMock()
        mock_loader.load_station_temperature_series = AsyncMock(return_value=test_series)

        mock_calculator = Mock()
        mock_calculator.compute_astronomical_features = Mock(return_value=test_astronomical_features)

        mock_renderer._get_kalshi_strikes_for_station = AsyncMock(return_value=[])

        invalid_coords = ("invalid", "coords")

        with (
            patch("common.chart_generator.renderers.weather.WeatherStationLoader", return_value=mock_loader),
            patch(
                "common.chart_generator.renderers.weather.AstronomicalCalculator",
                return_value=mock_calculator,
            ),
        ):
            result = await mock_renderer._create_weather_chart(TEST_STATION_ICAO, TEST_STATION_NAME, TEST_CITY_NAME, invalid_coords)

        assert result == TEST_CHART_PATH

        # Verify sanitized coordinates are None due to invalid input
        call_kwargs = mock_renderer._generate_unified_chart.call_args.kwargs
        assert call_kwargs["station_coordinates"] is None

    @pytest.mark.asyncio
    async def test_value_formatter_function(self, mock_renderer, test_series, test_coordinates, test_astronomical_features) -> None:
        """Test that value_formatter_func is correctly set."""
        mock_loader = AsyncMock()
        mock_loader.load_station_temperature_series = AsyncMock(return_value=test_series)

        mock_calculator = Mock()
        mock_calculator.compute_astronomical_features = Mock(return_value=test_astronomical_features)

        mock_renderer._get_kalshi_strikes_for_station = AsyncMock(return_value=[])

        with (
            patch("common.chart_generator.renderers.weather.WeatherStationLoader", return_value=mock_loader),
            patch(
                "common.chart_generator.renderers.weather.AstronomicalCalculator",
                return_value=mock_calculator,
            ),
        ):
            await mock_renderer._create_weather_chart(TEST_STATION_ICAO, TEST_STATION_NAME, TEST_CITY_NAME, test_coordinates)

        # Verify value_formatter_func
        call_kwargs = mock_renderer._generate_unified_chart.call_args.kwargs
        formatter = call_kwargs["value_formatter_func"]
        assert formatter(65.5) == "65.5°F"
        assert formatter(72.0) == "72.0°F"
        assert formatter(-5.3) == "-5.3°F"


class TestGenerateWeatherCharts:
    """Tests for generate_weather_charts method."""

    @pytest.mark.asyncio
    async def test_generate_charts_default_modules(self, mock_renderer) -> None:
        """Test generating weather charts with default modules."""
        expected_charts = [TEST_CHART_PATH]

        mock_orchestrator = AsyncMock()
        mock_orchestrator.generate_weather_charts = AsyncMock(return_value=expected_charts)

        with patch("common.chart_generator.renderers.weather.WeatherChartsOrchestrator") as mock_orch_class:
            mock_orch_class.return_value = mock_orchestrator

            result = await mock_renderer.generate_weather_charts()

        assert result == expected_charts
        mock_orch_class.assert_called_once()
        call_kwargs = mock_orch_class.call_args.kwargs
        assert call_kwargs["create_weather_chart_func"] == mock_renderer._create_weather_chart
        assert "config_loader_kwargs" in call_kwargs
        mock_orchestrator.generate_weather_charts.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_generate_charts_with_custom_os_module(self, mock_renderer) -> None:
        """Test generating weather charts with custom os module."""
        custom_os = MagicMock()
        mock_renderer._weather_config_os = custom_os

        expected_charts = [TEST_CHART_PATH]
        mock_orchestrator = AsyncMock()
        mock_orchestrator.generate_weather_charts = AsyncMock(return_value=expected_charts)

        with patch("common.chart_generator.renderers.weather.WeatherChartsOrchestrator") as mock_orch_class:
            mock_orch_class.return_value = mock_orchestrator

            result = await mock_renderer.generate_weather_charts()

        assert result == expected_charts
        call_kwargs = mock_orch_class.call_args.kwargs
        assert call_kwargs["config_loader_kwargs"]["os_module"] == custom_os

    @pytest.mark.asyncio
    async def test_generate_charts_with_custom_open_fn(self, mock_renderer) -> None:
        """Test generating weather charts with custom open function."""
        custom_open = MagicMock()
        mock_renderer._weather_config_open = custom_open

        expected_charts = [TEST_CHART_PATH]
        mock_orchestrator = AsyncMock()
        mock_orchestrator.generate_weather_charts = AsyncMock(return_value=expected_charts)

        with patch("common.chart_generator.renderers.weather.WeatherChartsOrchestrator") as mock_orch_class:
            mock_orch_class.return_value = mock_orchestrator

            result = await mock_renderer.generate_weather_charts()

        assert result == expected_charts
        call_kwargs = mock_orch_class.call_args.kwargs
        assert call_kwargs["config_loader_kwargs"]["open_fn"] == custom_open

    @pytest.mark.asyncio
    async def test_generate_charts_from_chart_module_attributes(self, mock_renderer) -> None:
        """Test generating weather charts using chart module attributes."""
        mock_chart_module = MagicMock()
        mock_os = MagicMock()
        mock_open_fn = MagicMock()
        mock_chart_module.os = mock_os
        mock_chart_module.open = mock_open_fn

        expected_charts = [TEST_CHART_PATH]
        mock_orchestrator = AsyncMock()
        mock_orchestrator.generate_weather_charts = AsyncMock(return_value=expected_charts)

        with (
            patch.dict("sys.modules", {"src.monitor.chart_generator": mock_chart_module}),
            patch("common.chart_generator.renderers.weather.WeatherChartsOrchestrator") as mock_orch_class,
        ):
            mock_orch_class.return_value = mock_orchestrator

            result = await mock_renderer.generate_weather_charts()

        assert result == expected_charts
        call_kwargs = mock_orch_class.call_args.kwargs
        assert call_kwargs["config_loader_kwargs"]["os_module"] == mock_os
        assert call_kwargs["config_loader_kwargs"]["open_fn"] == mock_open_fn
