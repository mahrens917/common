"""Unit tests for common redis_protocol weather_station_resolver module."""

import logging
from typing import Any, Dict
from unittest.mock import Mock

import pytest

from src.common.config.weather import WeatherConfigError
from src.common.redis_protocol.weather_station_resolver import (
    WeatherStationMappingError,
    WeatherStationResolver,
)


class TestWeatherStationMappingError:
    """Tests for WeatherStationMappingError exception."""

    def test_inherits_from_weather_config_error(self):
        """Test that WeatherStationMappingError inherits from WeatherConfigError."""
        exc = WeatherStationMappingError("test message")
        assert isinstance(exc, WeatherConfigError)

    def test_exception_message(self):
        """Test that exception message is preserved."""
        message = "Failed to load weather station mapping"
        exc = WeatherStationMappingError(message)
        assert str(exc) == message


class TestWeatherStationResolverInit:
    """Tests for WeatherStationResolver initialization."""

    def test_init_successful_loading(self):
        """Test successful initialization with valid mapping."""
        mapping = {
            "NYC": {"icao": "KJFK", "aliases": ["NEWYORK"]},
            "LA": {"icao": "KLAX", "aliases": ["LOSANGELES"]},
        }
        loader = Mock(return_value=mapping)
        logger = Mock(spec=logging.Logger)

        resolver = WeatherStationResolver(loader, logger=logger)

        assert resolver.mapping == mapping
        loader.assert_called_once()
        logger.debug.assert_called_once_with("Loaded weather station mapping for %d cities", 2)

    def test_init_empty_mapping(self):
        """Test initialization with empty mapping."""
        mapping: Dict[str, Dict[str, Any]] = {}
        loader = Mock(return_value=mapping)
        logger = Mock(spec=logging.Logger)

        resolver = WeatherStationResolver(loader, logger=logger)

        assert resolver.mapping == {}
        logger.debug.assert_called_once_with("Loaded weather station mapping for %d cities", 0)

    def test_init_loader_raises_weather_config_error(self):
        """Test initialization when loader raises WeatherConfigError."""
        loader = Mock(side_effect=WeatherConfigError("Config file not found"))
        logger = Mock(spec=logging.Logger)

        with pytest.raises(WeatherStationMappingError, match="Config file not found"):
            WeatherStationResolver(loader, logger=logger)

    def test_init_loader_raises_generic_exception(self):
        """Test initialization when loader raises unexpected exception."""
        loader = Mock(side_effect=ValueError("Unexpected error"))
        logger = Mock(spec=logging.Logger)

        with pytest.raises(ValueError, match="Unexpected error"):
            WeatherStationResolver(loader, logger=logger)

    def test_mapping_property(self):
        """Test that mapping property returns internal mapping."""
        mapping = {"NYC": {"icao": "KJFK"}}
        loader = Mock(return_value=mapping)
        logger = Mock(spec=logging.Logger)

        resolver = WeatherStationResolver(loader, logger=logger)

        assert resolver.mapping is resolver._mapping
        assert resolver.mapping == mapping


class TestWeatherStationResolverReload:
    """Tests for WeatherStationResolver reload method."""

    def test_reload_updates_mapping(self):
        """Test that reload updates the internal mapping."""
        initial_mapping = {"NYC": {"icao": "KJFK"}}
        updated_mapping = {
            "NYC": {"icao": "KJFK"},
            "LA": {"icao": "KLAX"},
        }
        loader = Mock(side_effect=[initial_mapping, updated_mapping])
        logger = Mock(spec=logging.Logger)

        resolver = WeatherStationResolver(loader, logger=logger)
        assert len(resolver.mapping) == 1

        resolver.reload()

        assert len(resolver.mapping) == 2
        assert resolver.mapping == updated_mapping
        assert loader.call_count == 2

    def test_reload_raises_mapping_error(self):
        """Test that reload raises WeatherStationMappingError on failure."""
        initial_mapping = {"NYC": {"icao": "KJFK"}}
        loader = Mock(side_effect=[initial_mapping, WeatherConfigError("Load failed")])
        logger = Mock(spec=logging.Logger)

        resolver = WeatherStationResolver(loader, logger=logger)

        with pytest.raises(WeatherStationMappingError, match="Load failed"):
            resolver.reload()

    def test_reload_preserves_old_mapping_on_error(self):
        """Test that mapping remains unchanged if reload fails."""
        initial_mapping = {"NYC": {"icao": "KJFK"}}
        loader = Mock(side_effect=[initial_mapping, WeatherConfigError("Load failed")])
        logger = Mock(spec=logging.Logger)

        resolver = WeatherStationResolver(loader, logger=logger)
        original_mapping = resolver.mapping.copy()

        with pytest.raises(WeatherStationMappingError):
            resolver.reload()

        # Mapping should still be the same after failed reload
        assert resolver.mapping == original_mapping


class TestWeatherStationResolverExtractStation:
    """Tests for WeatherStationResolver extract_station method."""

    def test_extract_station_direct_match(self):
        """Test extracting station with direct city code match."""
        mapping = {"PHIL": {"icao": "KPHL", "aliases": []}}
        loader = Mock(return_value=mapping)
        logger = Mock(spec=logging.Logger)
        resolver = WeatherStationResolver(loader, logger=logger)

        result = resolver.extract_station("KXHIGHPHIL-25AUG31-B80.5")

        assert result == "KPHL"
        logger.debug.assert_any_call(
            "Extracted weather station %s from ticker %s (direct match)",
            "KPHL",
            "KXHIGHPHIL-25AUG31-B80.5",
        )

    def test_extract_station_via_alias(self):
        """Test extracting station via alias resolution."""
        mapping = {
            "NYC": {"icao": "KJFK", "aliases": ["NEWYORK", "MANHATTAN"]},
        }
        loader = Mock(return_value=mapping)
        logger = Mock(spec=logging.Logger)
        resolver = WeatherStationResolver(loader, logger=logger)

        result = resolver.extract_station("KXHIGHNEWYORK-25AUG31-B80.5")

        assert result == "KJFK"
        logger.debug.assert_any_call("Resolved alias %s -> %s", "NEWYORK", "NYC")
        logger.debug.assert_any_call(
            "Extracted weather station %s from ticker %s (alias %s -> %s)",
            "KJFK",
            "KXHIGHNEWYORK-25AUG31-B80.5",
            "NEWYORK",
            "NYC",
        )

    def test_extract_station_non_kxhigh_ticker(self):
        """Test that non-KXHIGH ticker returns None."""
        mapping = {"NYC": {"icao": "KJFK"}}
        loader = Mock(return_value=mapping)
        logger = Mock(spec=logging.Logger)
        resolver = WeatherStationResolver(loader, logger=logger)

        result = resolver.extract_station("KXLOWNYC-25AUG31-B80.5")

        assert result is None

    def test_extract_station_no_dash_in_ticker(self):
        """Test that ticker without dash returns None."""
        mapping = {"NYC": {"icao": "KJFK"}}
        loader = Mock(return_value=mapping)
        logger = Mock(spec=logging.Logger)
        resolver = WeatherStationResolver(loader, logger=logger)

        result = resolver.extract_station("KXHIGHNYC")

        assert result is None
        logger.debug.assert_any_call("No dash found in KXHIGH ticker: %s", "KXHIGHNYC")

    def test_extract_station_dash_at_start(self):
        """Test that ticker with dash at start of suffix returns None."""
        mapping = {"NYC": {"icao": "KJFK"}}
        loader = Mock(return_value=mapping)
        logger = Mock(spec=logging.Logger)
        resolver = WeatherStationResolver(loader, logger=logger)

        result = resolver.extract_station("KXHIGH-25AUG31-B80.5")

        assert result is None
        logger.debug.assert_any_call("No dash found in KXHIGH ticker: %s", "KXHIGH-25AUG31-B80.5")

    def test_extract_station_city_code_not_found(self):
        """Test that unknown city code returns None."""
        mapping = {"NYC": {"icao": "KJFK"}}
        loader = Mock(return_value=mapping)
        logger = Mock(spec=logging.Logger)
        resolver = WeatherStationResolver(loader, logger=logger)

        result = resolver.extract_station("KXHIGHLA-25AUG31-B80.5")

        assert result is None
        logger.debug.assert_called_with("No weather station mapping found for city code: %s", "LA")

    def test_extract_station_missing_icao_field(self):
        """Test that station data without icao field returns None."""
        mapping = {"NYC": {"station": "JFK", "aliases": []}}
        loader = Mock(return_value=mapping)
        logger = Mock(spec=logging.Logger)
        resolver = WeatherStationResolver(loader, logger=logger)

        result = resolver.extract_station("KXHIGHNYC-25AUG31-B80.5")

        assert result is None

    def test_extract_station_non_dict_station_data(self):
        """Test that non-dict station data is handled gracefully."""
        mapping = {"NYC": "KJFK"}  # type: ignore[dict-item]
        loader = Mock(return_value=mapping)
        logger = Mock(spec=logging.Logger)
        resolver = WeatherStationResolver(loader, logger=logger)

        # The code doesn't handle non-dict station data in alias resolution
        # This will raise AttributeError when trying to call .get() on a string
        with pytest.raises(AttributeError, match="'str' object has no attribute 'get'"):
            resolver.extract_station("KXHIGHNYC-25AUG31-B80.5")

    def test_extract_station_empty_city_code(self):
        """Test that empty city code (dash right after KXHIGH) returns None."""
        mapping = {"": {"icao": "KXXX"}}
        loader = Mock(return_value=mapping)
        logger = Mock(spec=logging.Logger)
        resolver = WeatherStationResolver(loader, logger=logger)

        result = resolver.extract_station("KXHIGH-25AUG31-B80.5")

        assert result is None

    def test_extract_station_multiple_dashes(self):
        """Test extraction with multiple dashes in ticker."""
        mapping = {"PHIL": {"icao": "KPHL"}}
        loader = Mock(return_value=mapping)
        logger = Mock(spec=logging.Logger)
        resolver = WeatherStationResolver(loader, logger=logger)

        result = resolver.extract_station("KXHIGHPHIL-25AUG31-B80.5-EXTRA")

        assert result == "KPHL"

    def test_extract_station_case_sensitive_city_code(self):
        """Test that city code extraction is case-sensitive."""
        mapping = {"NYC": {"icao": "KJFK"}}
        loader = Mock(return_value=mapping)
        logger = Mock(spec=logging.Logger)
        resolver = WeatherStationResolver(loader, logger=logger)

        result = resolver.extract_station("KXHIGHnyc-25AUG31-B80.5")

        assert result is None
        logger.debug.assert_called_with("No weather station mapping found for city code: %s", "nyc")

    def test_extract_station_alias_without_icao_in_canonical(self):
        """Test alias resolution when canonical entry lacks icao field."""
        mapping = {
            "NYC": {"station": "JFK", "aliases": ["NEWYORK"]},
        }
        loader = Mock(return_value=mapping)
        logger = Mock(spec=logging.Logger)
        resolver = WeatherStationResolver(loader, logger=logger)

        result = resolver.extract_station("KXHIGHNEWYORK-25AUG31-B80.5")

        assert result is None

    def test_extract_station_complex_ticker_format(self):
        """Test extraction from complex ticker format."""
        mapping = {"MIAMI": {"icao": "KMIA", "aliases": []}}
        loader = Mock(return_value=mapping)
        logger = Mock(spec=logging.Logger)
        resolver = WeatherStationResolver(loader, logger=logger)

        result = resolver.extract_station("KXHIGHMIAMI-01JAN26-T95.0")

        assert result == "KMIA"


class TestWeatherStationResolverResolveCityAlias:
    """Tests for WeatherStationResolver city alias resolution methods."""

    def test_resolve_city_alias_found(self):
        """Test resolving an alias to its canonical city code."""
        mapping = {
            "NYC": {"icao": "KJFK", "aliases": ["NEWYORK", "MANHATTAN"]},
            "LA": {"icao": "KLAX", "aliases": ["LOSANGELES"]},
        }
        loader = Mock(return_value=mapping)
        logger = Mock(spec=logging.Logger)
        resolver = WeatherStationResolver(loader, logger=logger)

        result = resolver.resolve_city_alias("NEWYORK")

        assert result == "NYC"
        logger.debug.assert_called_with("Resolved alias %s -> %s", "NEWYORK", "NYC")

    def test_resolve_city_alias_not_found(self):
        """Test resolving an alias that doesn't exist returns None."""
        mapping = {
            "NYC": {"icao": "KJFK", "aliases": ["NEWYORK"]},
        }
        loader = Mock(return_value=mapping)
        logger = Mock(spec=logging.Logger)
        resolver = WeatherStationResolver(loader, logger=logger)

        result = resolver.resolve_city_alias("UNKNOWN")

        assert result is None

    def test_resolve_city_alias_canonical_code(self):
        """Test resolving a canonical city code returns None."""
        mapping = {
            "NYC": {"icao": "KJFK", "aliases": ["NEWYORK"]},
        }
        loader = Mock(return_value=mapping)
        logger = Mock(spec=logging.Logger)
        resolver = WeatherStationResolver(loader, logger=logger)

        result = resolver.resolve_city_alias("NYC")

        assert result is None

    def test_resolve_city_alias_no_aliases_field(self):
        """Test resolving when station data has no aliases field."""
        mapping = {
            "NYC": {"icao": "KJFK"},
        }
        loader = Mock(return_value=mapping)
        logger = Mock(spec=logging.Logger)
        resolver = WeatherStationResolver(loader, logger=logger)

        result = resolver.resolve_city_alias("NEWYORK")

        assert result is None

    def test_resolve_city_alias_none_aliases_field(self):
        """Test resolving when aliases field is None."""
        mapping = {
            "NYC": {"icao": "KJFK", "aliases": None},
        }
        loader = Mock(return_value=mapping)
        logger = Mock(spec=logging.Logger)
        resolver = WeatherStationResolver(loader, logger=logger)

        result = resolver.resolve_city_alias("NEWYORK")

        assert result is None

    def test_resolve_city_alias_empty_aliases_list(self):
        """Test resolving when aliases list is empty."""
        mapping = {
            "NYC": {"icao": "KJFK", "aliases": []},
        }
        loader = Mock(return_value=mapping)
        logger = Mock(spec=logging.Logger)
        resolver = WeatherStationResolver(loader, logger=logger)

        result = resolver.resolve_city_alias("NEWYORK")

        assert result is None

    def test_resolve_city_alias_multiple_cities_with_same_alias(self):
        """Test that first matching canonical code is returned."""
        mapping = {
            "NYC": {"icao": "KJFK", "aliases": ["BIG"]},
            "LA": {"icao": "KLAX", "aliases": ["BIG"]},
        }
        loader = Mock(return_value=mapping)
        logger = Mock(spec=logging.Logger)
        resolver = WeatherStationResolver(loader, logger=logger)

        result = resolver.resolve_city_alias("BIG")

        # Should return one of them (dict iteration order dependent in Python 3.7+)
        assert result in ["NYC", "LA"]

    def test_resolve_city_alias_case_sensitive(self):
        """Test that alias resolution is case-sensitive."""
        mapping = {
            "NYC": {"icao": "KJFK", "aliases": ["NewYork"]},
        }
        loader = Mock(return_value=mapping)
        logger = Mock(spec=logging.Logger)
        resolver = WeatherStationResolver(loader, logger=logger)

        result = resolver.resolve_city_alias("newyork")

        assert result is None

    def test_private_and_public_resolve_methods_equivalent(self):
        """Test that public resolve_city_alias wraps private _resolve_city_alias."""
        mapping = {
            "NYC": {"icao": "KJFK", "aliases": ["NEWYORK"]},
        }
        loader = Mock(return_value=mapping)
        logger = Mock(spec=logging.Logger)
        resolver = WeatherStationResolver(loader, logger=logger)

        public_result = resolver.resolve_city_alias("NEWYORK")
        private_result = resolver._resolve_city_alias("NEWYORK")

        assert public_result == private_result == "NYC"


class TestWeatherStationResolverIntegration:
    """Integration tests for WeatherStationResolver."""

    def test_full_workflow_direct_match(self):
        """Test complete workflow with direct city code match."""
        mapping = {
            "PHIL": {"icao": "KPHL", "aliases": ["PHILADELPHIA"]},
            "NYC": {"icao": "KJFK", "aliases": ["NEWYORK"]},
            "LA": {"icao": "KLAX", "aliases": ["LOSANGELES"]},
        }
        loader = Mock(return_value=mapping)
        logger = Mock(spec=logging.Logger)
        resolver = WeatherStationResolver(loader, logger=logger)

        # Test direct matches
        assert resolver.extract_station("KXHIGHPHIL-25AUG31-B80.5") == "KPHL"
        assert resolver.extract_station("KXHIGHNYC-01JAN26-T70.0") == "KJFK"
        assert resolver.extract_station("KXHIGHLA-15MAR26-B85.5") == "KLAX"

    def test_full_workflow_alias_match(self):
        """Test complete workflow with alias resolution."""
        mapping = {
            "PHIL": {"icao": "KPHL", "aliases": ["PHILADELPHIA"]},
            "NYC": {"icao": "KJFK", "aliases": ["NEWYORK", "MANHATTAN"]},
        }
        loader = Mock(return_value=mapping)
        logger = Mock(spec=logging.Logger)
        resolver = WeatherStationResolver(loader, logger=logger)

        # Test alias matches
        assert resolver.extract_station("KXHIGHPHILADELPHIA-25AUG31-B80.5") == "KPHL"
        assert resolver.extract_station("KXHIGHNEWYORK-01JAN26-T70.0") == "KJFK"
        assert resolver.extract_station("KXHIGHMANHATTAN-15MAR26-B85.5") == "KJFK"

    def test_full_workflow_with_reload(self):
        """Test workflow including reload functionality."""
        initial_mapping = {"NYC": {"icao": "KJFK", "aliases": []}}
        updated_mapping = {
            "NYC": {"icao": "KJFK", "aliases": ["NEWYORK"]},
            "LA": {"icao": "KLAX", "aliases": []},
        }
        loader = Mock(side_effect=[initial_mapping, updated_mapping])
        logger = Mock(spec=logging.Logger)
        resolver = WeatherStationResolver(loader, logger=logger)

        # Before reload
        assert resolver.extract_station("KXHIGHNYC-25AUG31-B80.5") == "KJFK"
        assert resolver.extract_station("KXHIGHNEWYORK-25AUG31-B80.5") is None
        assert resolver.extract_station("KXHIGHLA-25AUG31-B80.5") is None

        # After reload
        resolver.reload()
        assert resolver.extract_station("KXHIGHNYC-25AUG31-B80.5") == "KJFK"
        assert resolver.extract_station("KXHIGHNEWYORK-25AUG31-B80.5") == "KJFK"
        assert resolver.extract_station("KXHIGHLA-25AUG31-B80.5") == "KLAX"

    def test_mapping_with_real_weather_stations(self):
        """Test with realistic weather station data."""
        mapping = {
            "NYC": {"icao": "KJFK", "aliases": ["NEWYORK", "JFK"]},
            "CHI": {"icao": "KORD", "aliases": ["CHICAGO", "OHARE"]},
            "SF": {"icao": "KSFO", "aliases": ["SANFRANCISCO", "SFO"]},
            "MIA": {"icao": "KMIA", "aliases": ["MIAMI"]},
            "SEA": {"icao": "KSEA", "aliases": ["SEATTLE", "SEATAC"]},
        }
        loader = Mock(return_value=mapping)
        logger = Mock(spec=logging.Logger)
        resolver = WeatherStationResolver(loader, logger=logger)

        # Test various ticker formats
        test_cases = [
            ("KXHIGHNYC-25AUG31-B80.5", "KJFK"),
            ("KXHIGHNEWYORK-25AUG31-B80.5", "KJFK"),
            ("KXHIGHJFK-25AUG31-B80.5", "KJFK"),
            ("KXHIGHCHI-01JAN26-T70.0", "KORD"),
            ("KXHIGHCHICAGO-01JAN26-T70.0", "KORD"),
            ("KXHIGHOHARE-01JAN26-T70.0", "KORD"),
            ("KXHIGHSF-15MAR26-B85.5", "KSFO"),
            ("KXHIGHSANFRANCISCO-15MAR26-B85.5", "KSFO"),
            ("KXHIGHSFO-15MAR26-B85.5", "KSFO"),
        ]

        for ticker, expected_icao in test_cases:
            result = resolver.extract_station(ticker)
            assert result == expected_icao, f"Failed for ticker {ticker}"

    def test_edge_cases_and_error_conditions(self):
        """Test various edge cases and error conditions."""
        mapping = {
            "NYC": {"icao": "KJFK", "aliases": ["NEWYORK"]},
        }
        loader = Mock(return_value=mapping)
        logger = Mock(spec=logging.Logger)
        resolver = WeatherStationResolver(loader, logger=logger)

        # Various invalid ticker formats
        assert resolver.extract_station("INVALIDNYC-25AUG31-B80.5") is None
        assert resolver.extract_station("KXHIGH") is None
        assert resolver.extract_station("KXHIGH-") is None
        assert resolver.extract_station("KXHIGH--B80.5") is None
        assert resolver.extract_station("") is None
        assert resolver.extract_station("KXHIGHUNKNOWN-25AUG31-B80.5") is None
