"""Tests for weather_services.weatherruleengine_helpers.station_resolver module."""

from unittest.mock import MagicMock, patch

import pytest

from common.config.weather import WeatherConfigError
from common.weather_services.rule_engine_helpers import WeatherRuleEngineError
from common.weather_services.weatherruleengine_helpers.station_resolver import (
    StationResolver,
)


class TestStationResolverInit:
    """Tests for StationResolver initialization."""

    def test_uses_default_loader(self) -> None:
        """Test uses default loader when none provided."""
        from common.config.weather import load_weather_station_mapping

        resolver = StationResolver()

        assert resolver._loader is load_weather_station_mapping

    def test_uses_custom_loader(self) -> None:
        """Test uses custom loader when provided."""
        mock_loader = MagicMock(return_value={})
        resolver = StationResolver(station_mapping_loader=mock_loader)

        assert resolver._loader is mock_loader

    def test_initializes_empty_mapping(self) -> None:
        """Test initializes with empty mapping."""
        resolver = StationResolver()

        assert resolver._station_mapping == {}
        assert resolver._alias_index == {}


class TestStationResolverInitialize:
    """Tests for initialize method."""

    def test_loads_station_mapping(self) -> None:
        """Test loads station mapping."""
        mapping = {"KMIA": {"city": "Miami", "aliases": ["MIA"]}}
        mock_loader = MagicMock(return_value=mapping)

        resolver = StationResolver(station_mapping_loader=mock_loader)
        resolver.initialize()

        assert resolver._station_mapping == mapping
        mock_loader.assert_called_once()

    def test_builds_alias_index(self) -> None:
        """Test builds alias index."""
        mapping = {"KMIA": {"city": "Miami", "aliases": ["MIA"]}}
        mock_loader = MagicMock(return_value=mapping)

        with patch("common.weather_services.weatherruleengine_helpers.station_resolver.StationMappingIndexer") as mock_indexer:
            mock_indexer.build_alias_index.return_value = {"MIA": "KMIA"}

            resolver = StationResolver(station_mapping_loader=mock_loader)
            resolver.initialize()

            mock_indexer.build_alias_index.assert_called_once_with(mapping)

    def test_raises_on_config_error(self) -> None:
        """Test raises WeatherRuleEngineError on config error."""
        mock_loader = MagicMock(side_effect=WeatherConfigError("Config failed"))

        resolver = StationResolver(station_mapping_loader=mock_loader)

        with pytest.raises(WeatherRuleEngineError):
            resolver.initialize()


class TestStationResolverReloadMapping:
    """Tests for reload_mapping method."""

    def test_reloads_mapping(self) -> None:
        """Test reloads station mapping."""
        mapping1 = {"KMIA": {"city": "Miami"}}
        mapping2 = {"KJFK": {"city": "New York"}}
        call_count = [0]

        def loader():
            call_count[0] += 1
            return mapping1 if call_count[0] == 1 else mapping2

        resolver = StationResolver(station_mapping_loader=loader)
        resolver.initialize()
        assert resolver._station_mapping == mapping1

        resolver.reload_mapping()
        assert resolver._station_mapping == mapping2

    def test_rebuilds_alias_index(self) -> None:
        """Test rebuilds alias index on reload."""
        mapping = {"KMIA": {"city": "Miami"}}
        mock_loader = MagicMock(return_value=mapping)

        with patch("common.weather_services.weatherruleengine_helpers.station_resolver.StationMappingIndexer") as mock_indexer:
            mock_indexer.build_alias_index.return_value = {}

            resolver = StationResolver(station_mapping_loader=mock_loader)
            resolver.initialize()
            resolver.reload_mapping()

            # Should be called twice (init + reload)
            assert mock_indexer.build_alias_index.call_count == 2


class TestStationResolverResolveCityCode:
    """Tests for resolve_city_code method."""

    def test_resolves_city_code(self) -> None:
        """Test resolves city code for station."""
        mapping = {"KMIA": {"city_code": "MIA"}}
        mock_loader = MagicMock(return_value=mapping)

        with patch("common.weather_services.weatherruleengine_helpers.station_resolver.StationMappingIndexer") as mock_indexer:
            mock_indexer.build_alias_index.return_value = {}
            mock_indexer.resolve_city_code.return_value = "MIA"

            resolver = StationResolver(station_mapping_loader=mock_loader)
            resolver.initialize()
            result = resolver.resolve_city_code("KMIA")

            assert result == "MIA"
            mock_indexer.resolve_city_code.assert_called_once_with("KMIA", mapping, {})

    def test_returns_none_for_unknown_station(self) -> None:
        """Test returns None for unknown station."""
        mapping = {}
        mock_loader = MagicMock(return_value=mapping)

        with patch("common.weather_services.weatherruleengine_helpers.station_resolver.StationMappingIndexer") as mock_indexer:
            mock_indexer.build_alias_index.return_value = {}
            mock_indexer.resolve_city_code.return_value = None

            resolver = StationResolver(station_mapping_loader=mock_loader)
            resolver.initialize()
            result = resolver.resolve_city_code("KXYZ")

            assert result is None

    def test_uses_alias_index(self) -> None:
        """Test uses alias index for resolution."""
        mapping = {"KMIA": {"city_code": "MIA"}}
        mock_loader = MagicMock(return_value=mapping)

        with patch("common.weather_services.weatherruleengine_helpers.station_resolver.StationMappingIndexer") as mock_indexer:
            alias_index = {"MIA": "KMIA"}
            mock_indexer.build_alias_index.return_value = alias_index
            mock_indexer.resolve_city_code.return_value = "MIA"

            resolver = StationResolver(station_mapping_loader=mock_loader)
            resolver.initialize()
            resolver.resolve_city_code("MIA")

            mock_indexer.resolve_city_code.assert_called_once_with("MIA", mapping, alias_index)


class TestStationResolverLoadStationMapping:
    """Tests for _load_station_mapping method."""

    def test_returns_loader_result(self) -> None:
        """Test returns result from loader."""
        mapping = {"KMIA": {"city": "Miami"}}
        mock_loader = MagicMock(return_value=mapping)

        resolver = StationResolver(station_mapping_loader=mock_loader)
        result = resolver._load_station_mapping()

        assert result == mapping

    def test_wraps_config_error(self) -> None:
        """Test wraps WeatherConfigError in WeatherRuleEngineError."""
        mock_loader = MagicMock(side_effect=WeatherConfigError("Config failed"))

        resolver = StationResolver(station_mapping_loader=mock_loader)

        with pytest.raises(WeatherRuleEngineError) as exc_info:
            resolver._load_station_mapping()

        assert "Config failed" in str(exc_info.value)
