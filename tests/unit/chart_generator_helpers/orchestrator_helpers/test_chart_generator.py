"""Tests for chart_generator module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.chart_generator.exceptions import InsufficientDataError
from common.chart_generator_helpers.orchestrator_helpers.chart_generator import (
    generate_charts_for_stations,
)


class TestGenerateChartsForStations:
    """Tests for generate_charts_for_stations function."""

    @pytest.mark.asyncio
    async def test_empty_stations(self) -> None:
        """Test with empty weather stations dict."""
        mock_func = AsyncMock()

        with pytest.raises(InsufficientDataError, match="No weather data"):
            await generate_charts_for_stations({}, mock_func)

    @pytest.mark.asyncio
    async def test_single_station_success(self) -> None:
        """Test generating chart for single station."""
        mock_func = AsyncMock(return_value="/path/to/chart.png")
        stations = {"NYC": {"icao": "KJFK", "name": "JFK Airport", "city": "New York"}}

        result = await generate_charts_for_stations(stations, mock_func)

        assert result == ["/path/to/chart.png"]
        mock_func.assert_called_once()

    @pytest.mark.asyncio
    async def test_station_without_icao_skipped(self) -> None:
        """Test that stations without ICAO are skipped."""
        mock_func = AsyncMock(return_value="/path/to/chart.png")
        stations = {
            "NYC": {"name": "No ICAO Station"},
            "CHI": {"icao": "KORD", "name": "O'Hare", "city": "Chicago"},
        }

        result = await generate_charts_for_stations(stations, mock_func)

        assert len(result) == 1
        mock_func.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_stations(self) -> None:
        """Test generating charts for multiple stations."""
        mock_func = AsyncMock(side_effect=["/path/chart1.png", "/path/chart2.png"])
        stations = {
            "NYC": {"icao": "KJFK"},
            "CHI": {"icao": "KORD"},
        }

        result = await generate_charts_for_stations(stations, mock_func)

        assert len(result) == 2
        assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_insufficient_data_error_skips_station(self) -> None:
        """Test that InsufficientDataError skips station."""
        mock_func = AsyncMock(side_effect=[InsufficientDataError("No data"), "/path/chart.png"])
        stations = {
            "NYC": {"icao": "KJFK"},
            "CHI": {"icao": "KORD"},
        }

        result = await generate_charts_for_stations(stations, mock_func)

        assert result == ["/path/chart.png"]

    @pytest.mark.asyncio
    async def test_all_stations_fail(self) -> None:
        """Test raises error when all stations fail."""
        mock_func = AsyncMock(side_effect=InsufficientDataError("No data"))
        stations = {"NYC": {"icao": "KJFK"}}

        with pytest.raises(InsufficientDataError, match="No weather data"):
            await generate_charts_for_stations(stations, mock_func)

    @pytest.mark.asyncio
    async def test_uses_provided_chart_paths(self) -> None:
        """Test that provided chart_paths list is used."""
        mock_func = AsyncMock(return_value="/new/chart.png")
        stations = {"NYC": {"icao": "KJFK"}}
        existing_paths = ["/existing/chart.png"]

        result = await generate_charts_for_stations(stations, mock_func, chart_paths=existing_paths)

        assert result is existing_paths
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_passes_station_info_to_func(self) -> None:
        """Test that station info is passed to chart function."""
        mock_func = AsyncMock(return_value="/path/chart.png")
        stations = {
            "NYC": {
                "icao": "KJFK",
                "name": "JFK Airport",
                "city": "New York",
                "latitude": 40.6,
                "longitude": -73.8,
            }
        }

        await generate_charts_for_stations(stations, mock_func)

        mock_func.assert_called_once_with("KJFK", "JFK Airport", "New York", (40.6, -73.8))
