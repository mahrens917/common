"""Tests for chart_generator_helpers.weather_charts_orchestrator module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.chart_generator_helpers.weather_charts_orchestrator import (
    WeatherChartsOrchestrator,
)

TEST_STATION_ICAO = "KJFK"
TEST_CHART_PATH_1 = "/tmp/chart1.png"
TEST_CHART_PATH_2 = "/tmp/chart2.png"
TEST_CONFIG_KEY = "config_value"


class TestWeatherChartsOrchestratorInit:
    """Tests for WeatherChartsOrchestrator initialization."""

    def test_stores_create_func(self) -> None:
        """Test stores create weather chart function."""
        mock_func = MagicMock()

        orchestrator = WeatherChartsOrchestrator(create_weather_chart_func=mock_func)

        assert orchestrator.create_weather_chart_func is mock_func

    def test_stores_config_loader_kwargs_when_provided(self) -> None:
        """Test stores config loader kwargs when provided."""
        mock_func = MagicMock()
        config_kwargs = {"key": TEST_CONFIG_KEY}

        orchestrator = WeatherChartsOrchestrator(
            create_weather_chart_func=mock_func,
            config_loader_kwargs=config_kwargs,
        )

        assert orchestrator._config_loader_kwargs == {"key": TEST_CONFIG_KEY}

    def test_uses_empty_dict_when_config_loader_kwargs_none(self) -> None:
        """Test uses empty dict when config loader kwargs is None."""
        mock_func = MagicMock()

        orchestrator = WeatherChartsOrchestrator(
            create_weather_chart_func=mock_func,
            config_loader_kwargs=None,
        )

        assert orchestrator._config_loader_kwargs == {}

    def test_uses_empty_dict_when_config_loader_kwargs_not_provided(self) -> None:
        """Test uses empty dict when config loader kwargs not provided."""
        mock_func = MagicMock()

        orchestrator = WeatherChartsOrchestrator(create_weather_chart_func=mock_func)

        assert orchestrator._config_loader_kwargs == {}


class TestWeatherChartsOrchestratorGenerateWeatherCharts:
    """Tests for generate_weather_charts method."""

    @pytest.mark.asyncio
    async def test_loads_weather_station_config(self) -> None:
        """Test loads weather station configuration."""
        mock_func = MagicMock()
        config_kwargs = {"os_module": MagicMock()}

        with patch("common.chart_generator_helpers.orchestrator_helpers.config_loader.load_weather_station_config") as mock_load:
            mock_load.return_value = {}
            with patch("common.chart_generator_helpers.orchestrator_helpers.chart_generator.generate_charts_for_stations") as mock_generate:
                mock_generate.return_value = AsyncMock(return_value=None)

                orchestrator = WeatherChartsOrchestrator(
                    create_weather_chart_func=mock_func,
                    config_loader_kwargs=config_kwargs,
                )

                await orchestrator.generate_weather_charts()

                mock_load.assert_called_once_with(os_module=config_kwargs["os_module"])

    @pytest.mark.asyncio
    async def test_calls_generate_charts_for_stations(self) -> None:
        """Test calls generate_charts_for_stations with correct arguments."""
        mock_func = MagicMock()
        mock_stations = {"KJFK": {"icao": TEST_STATION_ICAO}}

        with patch("common.chart_generator_helpers.orchestrator_helpers.config_loader.load_weather_station_config") as mock_load:
            mock_load.return_value = mock_stations
            with patch("common.chart_generator_helpers.orchestrator_helpers.chart_generator.generate_charts_for_stations") as mock_generate:
                mock_generate.return_value = AsyncMock(return_value=None)

                orchestrator = WeatherChartsOrchestrator(create_weather_chart_func=mock_func)

                await orchestrator.generate_weather_charts()

                mock_generate.assert_called_once()
                call_args = mock_generate.call_args
                assert call_args[0][0] == mock_stations
                assert call_args[0][1] is mock_func

    @pytest.mark.asyncio
    async def test_returns_chart_paths_on_success(self) -> None:
        """Test returns chart paths on successful generation."""
        mock_func = MagicMock()
        expected_paths = [TEST_CHART_PATH_1, TEST_CHART_PATH_2]

        with patch("common.chart_generator_helpers.orchestrator_helpers.config_loader.load_weather_station_config") as mock_load:
            mock_load.return_value = {}
            with patch("common.chart_generator_helpers.orchestrator_helpers.chart_generator.generate_charts_for_stations") as mock_generate:

                async def populate_paths(stations, func, *, chart_paths):
                    chart_paths.extend(expected_paths)

                mock_generate.side_effect = populate_paths

                orchestrator = WeatherChartsOrchestrator(create_weather_chart_func=mock_func)

                result = await orchestrator.generate_weather_charts()

                assert result == expected_paths

    @pytest.mark.asyncio
    async def test_cleans_up_and_reraises_cancelled_error(self) -> None:
        """Test cleans up chart files and re-raises CancelledError."""
        mock_func = MagicMock()
        expected_paths = [TEST_CHART_PATH_1]

        with patch("common.chart_generator_helpers.orchestrator_helpers.config_loader.load_weather_station_config") as mock_load:
            mock_load.return_value = {}
            with patch("common.chart_generator_helpers.orchestrator_helpers.chart_generator.generate_charts_for_stations") as mock_generate:

                async def populate_and_raise(stations, func, *, chart_paths):
                    chart_paths.extend(expected_paths)
                    raise asyncio.CancelledError()

                mock_generate.side_effect = populate_and_raise

                with patch("common.chart_generator_helpers.orchestrator_helpers.cleanup_handler.cleanup_chart_files") as mock_cleanup:
                    orchestrator = WeatherChartsOrchestrator(create_weather_chart_func=mock_func)

                    with pytest.raises(asyncio.CancelledError):
                        await orchestrator.generate_weather_charts()

                    mock_cleanup.assert_called_once_with(expected_paths)

    @pytest.mark.asyncio
    async def test_cleans_up_and_reraises_ioerror(self) -> None:
        """Test cleans up chart files and re-raises IOError."""
        mock_func = MagicMock()
        expected_paths = [TEST_CHART_PATH_1, TEST_CHART_PATH_2]

        with patch("common.chart_generator_helpers.orchestrator_helpers.config_loader.load_weather_station_config") as mock_load:
            mock_load.return_value = {}
            with patch("common.chart_generator_helpers.orchestrator_helpers.chart_generator.generate_charts_for_stations") as mock_generate:

                async def populate_and_raise(stations, func, *, chart_paths):
                    chart_paths.extend(expected_paths)
                    raise IOError("IO failure")

                mock_generate.side_effect = populate_and_raise

                with patch("common.chart_generator_helpers.orchestrator_helpers.cleanup_handler.cleanup_chart_files") as mock_cleanup:
                    orchestrator = WeatherChartsOrchestrator(create_weather_chart_func=mock_func)

                    with pytest.raises(IOError):
                        await orchestrator.generate_weather_charts()

                    mock_cleanup.assert_called_once_with(expected_paths)

    @pytest.mark.asyncio
    async def test_cleans_up_and_reraises_oserror(self) -> None:
        """Test cleans up chart files and re-raises OSError."""
        mock_func = MagicMock()
        expected_paths = [TEST_CHART_PATH_1]

        with patch("common.chart_generator_helpers.orchestrator_helpers.config_loader.load_weather_station_config") as mock_load:
            mock_load.return_value = {}
            with patch("common.chart_generator_helpers.orchestrator_helpers.chart_generator.generate_charts_for_stations") as mock_generate:

                async def populate_and_raise(stations, func, *, chart_paths):
                    chart_paths.extend(expected_paths)
                    raise OSError("OS failure")

                mock_generate.side_effect = populate_and_raise

                with patch("common.chart_generator_helpers.orchestrator_helpers.cleanup_handler.cleanup_chart_files") as mock_cleanup:
                    orchestrator = WeatherChartsOrchestrator(create_weather_chart_func=mock_func)

                    with pytest.raises(OSError):
                        await orchestrator.generate_weather_charts()

                    mock_cleanup.assert_called_once_with(expected_paths)

    @pytest.mark.asyncio
    async def test_cleans_up_and_reraises_valueerror(self) -> None:
        """Test cleans up chart files and re-raises ValueError."""
        mock_func = MagicMock()
        expected_paths = [TEST_CHART_PATH_2]

        with patch("common.chart_generator_helpers.orchestrator_helpers.config_loader.load_weather_station_config") as mock_load:
            mock_load.return_value = {}
            with patch("common.chart_generator_helpers.orchestrator_helpers.chart_generator.generate_charts_for_stations") as mock_generate:

                async def populate_and_raise(stations, func, *, chart_paths):
                    chart_paths.extend(expected_paths)
                    raise ValueError("Value failure")

                mock_generate.side_effect = populate_and_raise

                with patch("common.chart_generator_helpers.orchestrator_helpers.cleanup_handler.cleanup_chart_files") as mock_cleanup:
                    orchestrator = WeatherChartsOrchestrator(create_weather_chart_func=mock_func)

                    with pytest.raises(ValueError):
                        await orchestrator.generate_weather_charts()

                    mock_cleanup.assert_called_once_with(expected_paths)

    @pytest.mark.asyncio
    async def test_cleans_up_and_reraises_runtimeerror(self) -> None:
        """Test cleans up chart files and re-raises RuntimeError."""
        mock_func = MagicMock()
        expected_paths = [TEST_CHART_PATH_1, TEST_CHART_PATH_2]

        with patch("common.chart_generator_helpers.orchestrator_helpers.config_loader.load_weather_station_config") as mock_load:
            mock_load.return_value = {}
            with patch("common.chart_generator_helpers.orchestrator_helpers.chart_generator.generate_charts_for_stations") as mock_generate:

                async def populate_and_raise(stations, func, *, chart_paths):
                    chart_paths.extend(expected_paths)
                    raise RuntimeError("Runtime failure")

                mock_generate.side_effect = populate_and_raise

                with patch("common.chart_generator_helpers.orchestrator_helpers.cleanup_handler.cleanup_chart_files") as mock_cleanup:
                    orchestrator = WeatherChartsOrchestrator(create_weather_chart_func=mock_func)

                    with pytest.raises(RuntimeError):
                        await orchestrator.generate_weather_charts()

                    mock_cleanup.assert_called_once_with(expected_paths)

    @pytest.mark.asyncio
    async def test_does_not_cleanup_on_success(self) -> None:
        """Test does not call cleanup when generation succeeds."""
        mock_func = MagicMock()

        with patch("common.chart_generator_helpers.orchestrator_helpers.config_loader.load_weather_station_config") as mock_load:
            mock_load.return_value = {}
            with patch("common.chart_generator_helpers.orchestrator_helpers.chart_generator.generate_charts_for_stations") as mock_generate:

                async def populate_paths(stations, func, *, chart_paths):
                    chart_paths.append(TEST_CHART_PATH_1)

                mock_generate.side_effect = populate_paths

                with patch("common.chart_generator_helpers.orchestrator_helpers.cleanup_handler.cleanup_chart_files") as mock_cleanup:
                    orchestrator = WeatherChartsOrchestrator(create_weather_chart_func=mock_func)

                    await orchestrator.generate_weather_charts()

                    mock_cleanup.assert_not_called()

    @pytest.mark.asyncio
    async def test_passes_empty_list_to_generate_charts(self) -> None:
        """Test passes empty list that gets populated with chart paths."""
        mock_func = MagicMock()

        with patch("common.chart_generator_helpers.orchestrator_helpers.config_loader.load_weather_station_config") as mock_load:
            mock_load.return_value = {}
            with patch("common.chart_generator_helpers.orchestrator_helpers.chart_generator.generate_charts_for_stations") as mock_generate:

                async def check_chart_paths(stations, func, *, chart_paths):
                    assert isinstance(chart_paths, list)
                    assert len(chart_paths) == 0

                mock_generate.side_effect = check_chart_paths

                orchestrator = WeatherChartsOrchestrator(create_weather_chart_func=mock_func)

                await orchestrator.generate_weather_charts()
