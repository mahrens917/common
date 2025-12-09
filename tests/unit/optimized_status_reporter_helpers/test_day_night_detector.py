"""Unit tests for day_night_detector."""

import json
import os
from unittest.mock import Mock, patch

import pytest

from src.common.optimized_status_reporter_helpers.day_night_detector import (
    DayNightDetector,
)


class TestDayNightDetector:
    """Tests for DayNightDetector."""

    @pytest.fixture
    def mock_moon_phase_calculator(self):
        """Mock MoonPhaseCalculator."""
        calculator = Mock()
        calculator.get_moon_phase_emoji.return_value = "🌕"
        return calculator

    @pytest.fixture
    def detector(self, mock_moon_phase_calculator):
        """DayNightDetector instance."""
        return DayNightDetector(mock_moon_phase_calculator)

    @pytest.fixture
    def mock_weather_config_file(self, tmp_path):
        """Create a mock weather_station_mapping.json file."""
        config_data = {
            "mappings": {
                "Station1": {"icao": "KNYC", "latitude": 40.71, "longitude": -74.01},
                "Station2": {"icao": "KLAX", "latitude": 33.94, "longitude": -118.40},
                "Station3": {"icao": None, "latitude": 10, "longitude": 10},  # Missing ICAO
                "Station4": {"icao": "KMIA"},  # Missing lat/lon
                "InvalidEntry": "not a dict",
            }
        }
        file_path = tmp_path / "config" / "weather_station_mapping.json"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w") as f:
            json.dump(config_data, f)
        return file_path

    @patch("os.path.join")
    @patch("os.path.dirname")
    @patch("json.load")
    def test_load_weather_station_coordinates_success(
        self, mock_json_load, mock_dirname, mock_join, detector, mock_weather_config_file
    ):
        """Test successful loading of coordinates."""
        mock_dirname.return_value = str(
            mock_weather_config_file.parent.parent.parent
        )  # Mimic the path up to the project root
        mock_join.return_value = str(mock_weather_config_file)  # The config file path

        mock_json_load.return_value = {
            "mappings": {
                "Station1": {"icao": "KNYC", "latitude": 40.71, "longitude": -74.01},
                "Station2": {"icao": "KLAX", "latitude": 33.94, "longitude": -118.40},
            }
        }

        detector.load_weather_station_coordinates()

        mock_json_load.assert_called_once()
        assert detector._station_coordinates == {
            "KNYC": {"latitude": 40.71, "longitude": -74.01},
            "KLAX": {"latitude": 33.94, "longitude": -118.40},
        }

    @patch("os.path.join")
    @patch("os.path.dirname")
    @patch("builtins.open", side_effect=OSError("File not found"))
    def test_load_weather_station_coordinates_file_not_found(
        self, mock_open, mock_dirname, mock_join, detector, mock_weather_config_file
    ):
        """Test handles file not found error."""
        mock_dirname.return_value = str(mock_weather_config_file.parent.parent.parent)
        mock_join.return_value = str(mock_weather_config_file)
        detector.load_weather_station_coordinates()
        assert detector._station_coordinates == {}

    @patch("os.path.join")
    @patch("os.path.dirname")
    @patch("builtins.open")
    @patch("json.load", side_effect=json.JSONDecodeError("Invalid JSON", doc="{}", pos=0))
    def test_load_weather_station_coordinates_invalid_json(
        self, mock_json_load, mock_open, mock_dirname, mock_join, detector, mock_weather_config_file
    ):
        """Test handles invalid JSON in config file."""
        mock_dirname.return_value = str(mock_weather_config_file.parent.parent.parent)
        mock_join.return_value = str(mock_weather_config_file)
        detector.load_weather_station_coordinates()
        assert detector._station_coordinates == {}

    @patch("os.path.join")
    @patch("os.path.dirname")
    @patch("builtins.open")
    @patch("json.load", return_value={"no_mappings_key": {}})
    def test_load_weather_station_coordinates_missing_mappings_key(
        self, mock_json_load, mock_open, mock_dirname, mock_join, detector, mock_weather_config_file
    ):
        """Test handles missing 'mappings' key."""
        mock_dirname.return_value = str(mock_weather_config_file.parent.parent.parent)
        mock_join.return_value = str(mock_weather_config_file)
        detector.load_weather_station_coordinates()
        assert detector._station_coordinates == {}

    @patch("os.path.join")
    @patch("os.path.dirname")
    @patch("builtins.open")
    @patch("json.load", return_value={"mappings": "not a dict"})
    def test_load_weather_station_coordinates_mappings_not_dict(
        self, mock_json_load, mock_open, mock_dirname, mock_join, detector, mock_weather_config_file
    ):
        """Test handles 'mappings' not being a dictionary."""
        mock_dirname.return_value = str(mock_weather_config_file.parent.parent.parent)
        mock_join.return_value = str(mock_weather_config_file)
        detector.load_weather_station_coordinates()
        assert detector._station_coordinates == {}

    @patch("os.path.join")
    @patch("os.path.dirname")
    @patch("builtins.open")
    @patch("json.load")
    def test_load_weather_station_coordinates_station_info_not_dict(
        self, mock_json_load, mock_open, mock_dirname, mock_join, detector, mock_weather_config_file
    ):
        """Test handles individual station info not being a dictionary."""
        mock_dirname.return_value = str(mock_weather_config_file.parent.parent.parent)
        mock_join.return_value = str(mock_weather_config_file)
        mock_json_load.return_value = {"mappings": {"Station1": "not a dict"}}
        detector.load_weather_station_coordinates()
        assert detector._station_coordinates == {}

    @patch("os.path.join")
    @patch("os.path.dirname")
    @patch("builtins.open")
    @patch("json.load")
    def test_load_weather_station_coordinates_incomplete_info(
        self, mock_json_load, mock_open, mock_dirname, mock_join, detector, mock_weather_config_file
    ):
        """Test handles incomplete station info in config file."""
        mock_dirname.return_value = str(mock_weather_config_file.parent.parent.parent)
        mock_join.return_value = str(mock_weather_config_file)
        mock_json_load.return_value = {
            "mappings": {
                "Station1": {"icao": "KNYC", "latitude": 40.71},  # Missing longitude
                "Station2": {"icao": "KLAX", "longitude": -118.40},  # Missing latitude
                "Station3": {"latitude": 10, "longitude": 10},  # Missing icao
            }
        }

        detector.load_weather_station_coordinates()
        assert detector._station_coordinates == {}  # All should be filtered out

    @pytest.fixture
    def detector_with_coordinates(self, detector):
        detector._station_coordinates = {"KNYC": {"latitude": 40.71, "longitude": -74.01}}
        return detector

    def test_get_day_night_icon_no_coordinates(self, detector):
        """Test returns empty string if no coordinates available for ICAO."""
        detector._station_coordinates = {}  # Explicitly ensure empty
        assert detector.get_day_night_icon("KNYC") == ""

    @patch(
        "src.common.optimized_status_reporter_helpers.day_night_detector.is_between_dawn_and_dusk",
        return_value=True,
    )
    def test_get_day_night_icon_daytime(
        self, mock_is_between_dawn_and_dusk, detector_with_coordinates
    ):
        """Test returns empty string for daytime."""
        assert detector_with_coordinates.get_day_night_icon("KNYC") == ""
        mock_is_between_dawn_and_dusk.assert_called_once_with(40.71, -74.01)

    @patch(
        "src.common.optimized_status_reporter_helpers.day_night_detector.is_between_dawn_and_dusk",
        return_value=False,
    )
    def test_get_day_night_icon_nighttime(
        self, mock_is_between_dawn_and_dusk, detector_with_coordinates, mock_moon_phase_calculator
    ):
        """Test returns moon phase emoji for nighttime."""
        assert detector_with_coordinates.get_day_night_icon("KNYC") == "🌕"
        mock_is_between_dawn_and_dusk.assert_called_once_with(40.71, -74.01)
        mock_moon_phase_calculator.get_moon_phase_emoji.assert_called_once()

    @patch(
        "src.common.optimized_status_reporter_helpers.day_night_detector.is_between_dawn_and_dusk",
        side_effect=ValueError("Test error"),
    )
    def test_get_day_night_icon_exception_handling(
        self, mock_is_between_dawn_and_dusk, detector_with_coordinates
    ):
        """Test get_day_night_icon returns empty string on exception."""
        assert detector_with_coordinates.get_day_night_icon("KNYC") == ""
        mock_is_between_dawn_and_dusk.assert_called_once_with(40.71, -74.01)
