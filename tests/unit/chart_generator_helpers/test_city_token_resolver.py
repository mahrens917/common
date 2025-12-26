"""Tests for chart_generator_helpers.city_token_resolver module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from common.chart_generator_helpers.city_token_resolver import CityTokenResolver


class TestCityTokenResolverExtractTokensForStation:
    """Tests for _extract_tokens_for_station method."""

    def test_extracts_tokens_for_matching_icao(self) -> None:
        """Test extracts tokens for matching ICAO code."""
        resolver = CityTokenResolver()
        mapping_data = {
            "mappings": {
                "miami": {
                    "icao": "KMIA",
                    "aliases": ["MIA", "MIAMI"],
                }
            }
        }

        tokens, canonical = resolver._extract_tokens_for_station("KMIA", mapping_data)

        assert "MIAMI" in tokens
        assert "MIA" in tokens
        assert "KMIA" in tokens
        assert canonical == "MIAMI"

    def test_returns_empty_for_no_match(self) -> None:
        """Test returns empty for no matching ICAO."""
        resolver = CityTokenResolver()
        mapping_data = {
            "mappings": {
                "miami": {
                    "icao": "KMIA",
                }
            }
        }

        tokens, canonical = resolver._extract_tokens_for_station("KJFK", mapping_data)

        assert tokens == []
        assert canonical is None

    def test_handles_no_aliases(self) -> None:
        """Test handles station without aliases."""
        resolver = CityTokenResolver()
        mapping_data = {
            "mappings": {
                "miami": {
                    "icao": "KMIA",
                }
            }
        }

        tokens, canonical = resolver._extract_tokens_for_station("KMIA", mapping_data)

        assert "MIAMI" in tokens
        assert "KMIA" in tokens
        assert canonical == "MIAMI"

    def test_handles_non_list_aliases(self) -> None:
        """Test handles non-list aliases gracefully."""
        resolver = CityTokenResolver()
        mapping_data = {
            "mappings": {
                "miami": {
                    "icao": "KMIA",
                    "aliases": "not_a_list",  # Invalid
                }
            }
        }

        tokens, canonical = resolver._extract_tokens_for_station("KMIA", mapping_data)

        # Should still work, just without aliases
        assert "MIAMI" in tokens
        assert "KMIA" in tokens
        assert canonical == "MIAMI"

    def test_uppercases_tokens(self) -> None:
        """Test all tokens are uppercased."""
        resolver = CityTokenResolver()
        mapping_data = {
            "mappings": {
                "miami": {
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
                "miami": {
                    "icao": "KMIA",
                    "aliases": ["MIA"],
                }
            }
        }

        with patch.object(resolver, "_load_mapping_data", return_value=mapping_data):
            tokens, canonical = await resolver.get_city_tokens_for_icao("KMIA")

        assert "MIA" in tokens
        assert "KMIA" in tokens
        assert canonical == "MIAMI"

    @pytest.mark.asyncio
    async def test_handles_load_error(self) -> None:
        """Test handles mapping load error gracefully."""
        resolver = CityTokenResolver()

        with patch.object(resolver, "_load_mapping_data", side_effect=OSError("File not found")):
            tokens, canonical = await resolver.get_city_tokens_for_icao("KMIA")

        assert tokens == []
        assert canonical is None

    @pytest.mark.asyncio
    async def test_handles_json_decode_error(self) -> None:
        """Test handles JSON decode error gracefully."""
        resolver = CityTokenResolver()

        with patch.object(
            resolver, "_load_mapping_data", side_effect=json.JSONDecodeError("msg", "doc", 0)
        ):
            tokens, canonical = await resolver.get_city_tokens_for_icao("KMIA")

        assert tokens == []
        assert canonical is None

    @pytest.mark.asyncio
    async def test_handles_key_error(self) -> None:
        """Test handles KeyError gracefully."""
        resolver = CityTokenResolver()

        with patch.object(resolver, "_load_mapping_data", side_effect=KeyError("mappings")):
            tokens, canonical = await resolver.get_city_tokens_for_icao("KMIA")

        assert tokens == []
        assert canonical is None
