"""Tests for kalshi_catalog_helpers.station_loader module."""

import json
import tempfile
from pathlib import Path

import pytest

from common.kalshi_catalog_helpers.station_loader import WeatherStationLoader


class TestWeatherStationLoaderInit:
    """Tests for WeatherStationLoader initialization."""

    def test_stores_config_root(self) -> None:
        """Test initialization stores config root."""
        config_root = Path("/some/path")

        loader = WeatherStationLoader(config_root)

        assert loader._config_root == config_root


class TestWeatherStationLoaderLoadStationTokens:
    """Tests for load_station_tokens method."""

    def test_returns_defaults_when_file_missing(self) -> None:
        """Test returns default stations when file is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = WeatherStationLoader(Path(tmpdir))

            result = loader.load_station_tokens()

        assert "MIA" in result
        assert "NYC" in result
        assert "LAX" in result

    def test_returns_defaults_when_invalid_json(self) -> None:
        """Test returns defaults when JSON is invalid."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mapping_file = Path(tmpdir) / "weather_station_mapping.json"
            mapping_file.write_text("not valid json {")

            loader = WeatherStationLoader(Path(tmpdir))

            result = loader.load_station_tokens()

        assert "MIA" in result
        assert "NYC" in result

    def test_returns_defaults_when_missing_mappings(self) -> None:
        """Test returns defaults when mappings key missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mapping_file = Path(tmpdir) / "weather_station_mapping.json"
            mapping_file.write_text(json.dumps({"other_key": {}}))

            loader = WeatherStationLoader(Path(tmpdir))

            result = loader.load_station_tokens()

        assert "MIA" in result

    def test_extracts_tokens_from_mappings(self) -> None:
        """Test extracts tokens from valid mappings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mapping_file = Path(tmpdir) / "weather_station_mapping.json"
            mapping_file.write_text(
                json.dumps(
                    {
                        "mappings": {
                            "miami": {
                                "icao": "KMIA",
                                "aliases": ["MIA", "MIAMI"],
                            },
                            "new_york": {
                                "icao": "KJFK",
                                "aliases": ["NYC", "JFK"],
                            },
                        }
                    }
                )
            )

            loader = WeatherStationLoader(Path(tmpdir))

            result = loader.load_station_tokens()

        assert "KMIA" in result
        assert "MIA" in result
        assert "MIAMI" in result
        assert "KJFK" in result
        assert "NYC" in result

    def test_returns_defaults_when_no_tokens_found(self) -> None:
        """Test returns defaults when mappings are empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mapping_file = Path(tmpdir) / "weather_station_mapping.json"
            mapping_file.write_text(json.dumps({"mappings": {}}))

            loader = WeatherStationLoader(Path(tmpdir))

            result = loader.load_station_tokens()

        assert "MIA" in result


class TestWeatherStationLoaderExtractTokens:
    """Tests for token extraction methods."""

    def test_add_code_token(self) -> None:
        """Test adds uppercase code token."""
        tokens: set[str] = set()

        WeatherStationLoader._add_code_token(tokens, "miami")

        assert "MIAMI" in tokens

    def test_add_code_token_non_string(self) -> None:
        """Test skips non-string codes."""
        tokens: set[str] = set()

        WeatherStationLoader._add_code_token(tokens, 123)

        assert len(tokens) == 0

    def test_add_alias_tokens(self) -> None:
        """Test adds uppercase alias tokens."""
        tokens: set[str] = set()
        details = {"aliases": ["mia", "miami"]}

        WeatherStationLoader._add_alias_tokens(tokens, details)

        assert "MIA" in tokens
        assert "MIAMI" in tokens

    def test_add_alias_tokens_no_aliases(self) -> None:
        """Test handles missing aliases."""
        tokens: set[str] = set()
        details = {}

        WeatherStationLoader._add_alias_tokens(tokens, details)

        assert len(tokens) == 0

    def test_add_alias_tokens_non_list(self) -> None:
        """Test handles non-list aliases."""
        tokens: set[str] = set()
        details = {"aliases": "not_a_list"}

        WeatherStationLoader._add_alias_tokens(tokens, details)

        assert len(tokens) == 0

    def test_add_icao_token(self) -> None:
        """Test adds uppercase ICAO token."""
        tokens: set[str] = set()
        details = {"icao": "kmia"}

        WeatherStationLoader._add_icao_token(tokens, details)

        assert "KMIA" in tokens

    def test_add_icao_token_missing(self) -> None:
        """Test handles missing ICAO."""
        tokens: set[str] = set()
        details = {}

        WeatherStationLoader._add_icao_token(tokens, details)

        assert len(tokens) == 0

    def test_add_icao_token_non_string(self) -> None:
        """Test handles non-string ICAO."""
        tokens: set[str] = set()
        details = {"icao": 12345}

        WeatherStationLoader._add_icao_token(tokens, details)

        assert len(tokens) == 0


class TestWeatherStationLoaderDefaultStations:
    """Tests for default station list."""

    def test_default_stations_include_major_cities(self) -> None:
        """Test default stations include major cities."""
        defaults = WeatherStationLoader._DEFAULT_WEATHER_STATIONS

        assert "MIA" in defaults
        assert "NYC" in defaults
        assert "LAX" in defaults
        assert "CHI" in defaults
