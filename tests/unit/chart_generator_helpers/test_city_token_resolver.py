"""Tests for chart_generator_helpers.city_token_resolver module."""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest

from common.chart_generator_helpers.city_token_resolver import CityTokenResolver

# Test constants (data_guard requirement)
TEST_ICAO_CODE_KMIA = "KMIA"
TEST_ICAO_CODE_KJFK = "KJFK"
TEST_CITY_CODE_MIAMI = "miami"
TEST_ALIAS_MIA = "MIA"
TEST_ALIAS_MIAMI = "MIAMI"
TEST_CONFIG_PATH = "config/weather_station_mapping.json"
TEST_JSON_CONTENT = '{"mappings": {"test": {"icao": "TEST"}}}'
TEST_ERROR_MESSAGE = "File not found"


class TestCityTokenResolverExtractTokensForStation:
    """Tests for _extract_tokens_for_station method."""

    def test_extracts_tokens_for_matching_icao(self) -> None:
        """Test extracts tokens for matching ICAO code."""
        resolver = CityTokenResolver()
        mapping_data = {
            "mappings": {
                TEST_CITY_CODE_MIAMI: {
                    "icao": TEST_ICAO_CODE_KMIA,
                    "aliases": [TEST_ALIAS_MIA, TEST_ALIAS_MIAMI],
                }
            }
        }

        tokens, canonical = resolver._extract_tokens_for_station(TEST_ICAO_CODE_KMIA, mapping_data)

        assert TEST_ALIAS_MIAMI in tokens
        assert TEST_ALIAS_MIA in tokens
        assert TEST_ICAO_CODE_KMIA in tokens
        assert canonical == TEST_ALIAS_MIAMI

    def test_returns_empty_for_no_match(self) -> None:
        """Test returns empty for no matching ICAO."""
        resolver = CityTokenResolver()
        mapping_data = {
            "mappings": {
                TEST_CITY_CODE_MIAMI: {
                    "icao": TEST_ICAO_CODE_KMIA,
                }
            }
        }

        tokens, canonical = resolver._extract_tokens_for_station(TEST_ICAO_CODE_KJFK, mapping_data)

        assert tokens == []
        assert canonical is None

    def test_handles_no_aliases(self) -> None:
        """Test handles station without aliases."""
        resolver = CityTokenResolver()
        mapping_data = {
            "mappings": {
                TEST_CITY_CODE_MIAMI: {
                    "icao": TEST_ICAO_CODE_KMIA,
                }
            }
        }

        tokens, canonical = resolver._extract_tokens_for_station(TEST_ICAO_CODE_KMIA, mapping_data)

        assert TEST_ALIAS_MIAMI in tokens
        assert TEST_ICAO_CODE_KMIA in tokens
        assert canonical == TEST_ALIAS_MIAMI

    def test_handles_non_list_aliases(self) -> None:
        """Test handles non-list aliases gracefully."""
        resolver = CityTokenResolver()
        mapping_data = {
            "mappings": {
                TEST_CITY_CODE_MIAMI: {
                    "icao": TEST_ICAO_CODE_KMIA,
                    "aliases": "not_a_list",  # Invalid
                }
            }
        }

        tokens, canonical = resolver._extract_tokens_for_station(TEST_ICAO_CODE_KMIA, mapping_data)

        # Should still work, just without aliases
        assert TEST_ALIAS_MIAMI in tokens
        assert TEST_ICAO_CODE_KMIA in tokens
        assert canonical == TEST_ALIAS_MIAMI

    def test_uppercases_tokens(self) -> None:
        """Test all tokens are uppercased."""
        resolver = CityTokenResolver()
        mapping_data = {
            "mappings": {
                TEST_CITY_CODE_MIAMI: {
                    "icao": "kmia",  # lowercase
                    "aliases": ["mia"],
                }
            }
        }

        tokens, canonical = resolver._extract_tokens_for_station("kmia", mapping_data)

        assert all(token.isupper() for token in tokens)


class TestCityTokenResolverGetCityTokensForIcao:
    """Tests for get_city_tokens_for_icao method."""

    @pytest.mark.asyncio
    async def test_returns_tokens_for_valid_icao(self) -> None:
        """Test returns tokens for valid ICAO code."""
        resolver = CityTokenResolver()
        mapping_data = {
            "mappings": {
                TEST_CITY_CODE_MIAMI: {
                    "icao": TEST_ICAO_CODE_KMIA,
                    "aliases": [TEST_ALIAS_MIA],
                }
            }
        }

        with patch.object(resolver, "_load_mapping_data", return_value=mapping_data):
            tokens, canonical = await resolver.get_city_tokens_for_icao(TEST_ICAO_CODE_KMIA)

        assert TEST_ALIAS_MIA in tokens
        assert TEST_ICAO_CODE_KMIA in tokens
        assert canonical == TEST_ALIAS_MIAMI

    @pytest.mark.asyncio
    async def test_handles_load_error(self) -> None:
        """Test handles mapping load error gracefully."""
        resolver = CityTokenResolver()

        with patch.object(resolver, "_load_mapping_data", side_effect=OSError(TEST_ERROR_MESSAGE)):
            tokens, canonical = await resolver.get_city_tokens_for_icao(TEST_ICAO_CODE_KMIA)

        assert tokens == []
        assert canonical is None

    @pytest.mark.asyncio
    async def test_handles_json_decode_error(self) -> None:
        """Test handles JSON decode error gracefully."""
        resolver = CityTokenResolver()

        with patch.object(resolver, "_load_mapping_data", side_effect=json.JSONDecodeError("msg", "doc", 0)):
            tokens, canonical = await resolver.get_city_tokens_for_icao(TEST_ICAO_CODE_KMIA)

        assert tokens == []
        assert canonical is None

    @pytest.mark.asyncio
    async def test_handles_key_error(self) -> None:
        """Test handles KeyError gracefully."""
        resolver = CityTokenResolver()

        with patch.object(resolver, "_load_mapping_data", side_effect=KeyError("mappings")):
            tokens, canonical = await resolver.get_city_tokens_for_icao(TEST_ICAO_CODE_KMIA)

        assert tokens == []
        assert canonical is None


class TestCityTokenResolverLoadMappingData:
    """Tests for _load_mapping_data method."""

    def test_loads_mapping_data_successfully(self) -> None:
        """Test successfully loads mapping data from config file."""
        resolver = CityTokenResolver()
        mapping_data = {"mappings": {"test": {"icao": "TEST"}}}

        mock_file = mock_open(read_data=TEST_JSON_CONTENT)

        with patch("builtins.open", mock_file):
            result = resolver._load_mapping_data()

        assert result == mapping_data
        mock_file.assert_called_once()

    def test_uses_module_attributes_when_available(self) -> None:
        """Test uses os and open from chart_generator module when available."""
        resolver = CityTokenResolver()

        # Create mock module with custom os and open
        mock_cg_module = Mock()
        mock_os_module = Mock()
        mock_os_module.path.join = Mock(return_value="/fake/path/config/weather_station_mapping.json")
        mock_cg_module.os = mock_os_module

        mock_open_fn = mock_open(read_data=TEST_JSON_CONTENT)
        mock_cg_module.open = mock_open_fn

        with patch.dict(sys.modules, {"src.monitor.chart_generator": mock_cg_module}):
            result = resolver._load_mapping_data()

        # Verify it used the module's os.path.join
        mock_os_module.path.join.assert_called_once()
        # Verify it used the module's open function
        mock_open_fn.assert_called_once()

    def test_raises_oserror_on_path_resolution_failure(self) -> None:
        """Test raises OSError when path resolution fails."""
        resolver = CityTokenResolver()

        # Mock Path to raise IndexError on parents access
        with patch("common.chart_generator_helpers.city_token_resolver.Path") as mock_path:
            mock_file = Mock()
            # Make parents subscriptable but raise IndexError
            mock_parents = Mock()
            mock_parents.__getitem__ = Mock(side_effect=IndexError("list index out of range"))
            mock_file.parents = mock_parents
            mock_path.return_value = mock_file

            with pytest.raises(OSError) as exc_info:
                resolver._load_mapping_data()

            assert "Unable to resolve weather station mapping path" in str(exc_info.value)
