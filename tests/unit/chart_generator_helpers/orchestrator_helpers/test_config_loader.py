"""Tests for config_loader module."""

import json
from unittest.mock import MagicMock, mock_open, patch

import pytest

from common.chart_generator.exceptions import InsufficientDataError
from common.chart_generator_helpers.orchestrator_helpers.config_loader import (
    load_weather_station_config,
)


class TestLoadWeatherStationConfig:
    """Tests for load_weather_station_config function."""

    def test_success_with_mappings(self) -> None:
        """Test successful loading with mappings."""
        mock_loader = MagicMock()
        mock_loader.load_json_file.return_value = {"mappings": {"NYC": {"icao": "KJFK"}}}

        with patch(
            "common.chart_generator_helpers.orchestrator_helpers.config_loader._base_loader",
            mock_loader,
        ):
            result = load_weather_station_config()

        assert result == {"NYC": {"icao": "KJFK"}}

    def test_raises_error_when_mappings_missing(self) -> None:
        """Test raises error when mappings key is missing."""
        mock_loader = MagicMock()
        mock_loader.load_json_file.return_value = {"other_key": "value"}

        with patch(
            "common.chart_generator_helpers.orchestrator_helpers.config_loader._base_loader",
            mock_loader,
        ):
            with pytest.raises(InsufficientDataError, match="No weather stations"):
                load_weather_station_config()

    def test_raises_error_when_mappings_empty(self) -> None:
        """Test raises error when mappings is empty."""
        mock_loader = MagicMock()
        mock_loader.load_json_file.return_value = {"mappings": {}}

        with patch(
            "common.chart_generator_helpers.orchestrator_helpers.config_loader._base_loader",
            mock_loader,
        ):
            with pytest.raises(InsufficientDataError, match="No weather stations"):
                load_weather_station_config()

    def test_raises_error_on_file_not_found(self) -> None:
        """Test raises error when config file not found."""
        mock_loader = MagicMock()
        mock_loader.load_json_file.side_effect = FileNotFoundError()

        with patch(
            "common.chart_generator_helpers.orchestrator_helpers.config_loader._base_loader",
            mock_loader,
        ):
            with pytest.raises(InsufficientDataError, match="Failed to load"):
                load_weather_station_config()

    def test_raises_error_on_json_decode_error(self) -> None:
        """Test raises error on JSON decode error."""
        mock_loader = MagicMock()
        mock_loader.load_json_file.side_effect = json.JSONDecodeError("error", "doc", 0)

        with patch(
            "common.chart_generator_helpers.orchestrator_helpers.config_loader._base_loader",
            mock_loader,
        ):
            with pytest.raises(InsufficientDataError, match="Failed to load"):
                load_weather_station_config()

    def test_custom_open_fn(self) -> None:
        """Test loading with custom os_module and open_fn."""
        mock_os = MagicMock()
        mock_os.path.join.return_value = "config/weather_station_mapping.json"
        config_data = json.dumps({"mappings": {"NYC": {"icao": "KJFK"}}})

        result = load_weather_station_config(os_module=mock_os, open_fn=mock_open(read_data=config_data))

        assert result == {"NYC": {"icao": "KJFK"}}
