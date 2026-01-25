"""Tests for llm_extractor extractor module."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.llm_extractor.extractor import (
    MarketExtractor,
    _extraction_to_redis_map,
    _get_redis_key,
    _get_ttl,
    _redis_map_to_extraction,
)
from common.llm_extractor.models import MarketExtraction


class TestGetRedisKey:
    """Tests for _get_redis_key."""

    def test_kalshi_key_format(self) -> None:
        """Test Redis key format for Kalshi markets."""
        assert _get_redis_key("KXETHD-26JAN", "kalshi") == "market:extracted:kalshi:KXETHD-26JAN"

    def test_poly_key_format(self) -> None:
        """Test Redis key format for Poly markets."""
        assert _get_redis_key("cond-123", "poly") == "market:extracted:poly:cond-123"


class TestGetTtl:
    """Tests for _get_ttl."""

    def test_kalshi_ttl_is_24h(self) -> None:
        """Test that Kalshi TTL is 24 hours."""
        assert _get_ttl("kalshi") == 86400

    def test_poly_ttl_is_7d(self) -> None:
        """Test that Poly TTL is 7 days."""
        assert _get_ttl("poly") == 604800


class TestExtractionToRedisMap:
    """Tests for _extraction_to_redis_map."""

    def test_maps_required_fields(self) -> None:
        """Test that required fields are always present in the map."""
        extraction = MarketExtraction(
            market_id="m1",
            platform="poly",
            category="Crypto",
            underlying="BTC",
            subject="BTC",
            entity="BTC price",
            scope="above 100000",
        )
        result = _extraction_to_redis_map(extraction)
        assert result["category"] == "Crypto"
        assert result["underlying"] == "BTC"
        assert result["subject"] == "BTC"
        assert result["entity"] == "BTC price"
        assert result["scope"] == "above 100000"
        assert result["platform"] == "poly"
        assert result["is_conjunction"] == "False"
        assert result["is_union"] == "False"

    def test_includes_optional_strike_fields(self) -> None:
        """Test that strike fields are included when present."""
        extraction = MarketExtraction(
            market_id="m1",
            platform="kalshi",
            category="Crypto",
            underlying="ETH",
            subject="ETH",
            entity="ETH price",
            scope="between 3500 and 3600",
            floor_strike=3500.0,
            cap_strike=3600.0,
        )
        result = _extraction_to_redis_map(extraction)
        assert result["floor_strike"] == "3500.0"
        assert result["cap_strike"] == "3600.0"

    def test_excludes_none_optional_fields(self) -> None:
        """Test that None optional fields are not in the map."""
        extraction = MarketExtraction(
            market_id="m1",
            platform="poly",
            category="Crypto",
            underlying="BTC",
            subject="BTC",
            entity="BTC price",
            scope="above 100000",
        )
        result = _extraction_to_redis_map(extraction)
        assert "floor_strike" not in result
        assert "cap_strike" not in result
        assert "parent_entity" not in result
        assert "parent_scope" not in result

    def test_serializes_conjunction_scopes(self) -> None:
        """Test that conjunction_scopes are JSON-serialized."""
        extraction = MarketExtraction(
            market_id="m1",
            platform="poly",
            category="Crypto",
            underlying="BTC",
            subject="BTC",
            entity="BTC and ETH",
            scope="both above",
            is_conjunction=True,
            conjunction_scopes=("BTC above 100000", "ETH above 5000"),
        )
        result = _extraction_to_redis_map(extraction)
        assert json.loads(result["conjunction_scopes"]) == ["BTC above 100000", "ETH above 5000"]


class TestRedisMapToExtraction:
    """Tests for _redis_map_to_extraction."""

    def test_reconstructs_extraction_from_map(self) -> None:
        """Test round-trip: extraction -> redis map -> extraction."""
        data = {
            b"category": b"Crypto",
            b"underlying": b"BTC",
            b"subject": b"BTC",
            b"entity": b"BTC price",
            b"scope": b"above 100000",
            b"platform": b"poly",
            b"is_conjunction": b"False",
            b"is_union": b"False",
            b"floor_strike": b"100000.0",
        }
        result = _redis_map_to_extraction("cond-1", "poly", data)
        assert result.market_id == "cond-1"
        assert result.platform == "poly"
        assert result.category == "Crypto"
        assert result.underlying == "BTC"
        assert result.floor_strike == 100000.0
        assert result.cap_strike is None
        assert result.is_conjunction is False

    def test_handles_conjunction_and_union(self) -> None:
        """Test parsing conjunction and union fields from Redis."""
        data = {
            b"category": b"Crypto",
            b"underlying": b"BTC",
            b"subject": b"BTC",
            b"entity": b"BTC and ETH",
            b"scope": b"both above",
            b"platform": b"poly",
            b"is_conjunction": b"True",
            b"conjunction_scopes": b'["BTC above 100000", "ETH above 5000"]',
            b"is_union": b"False",
        }
        result = _redis_map_to_extraction("m1", "poly", data)
        assert result.is_conjunction is True
        assert result.conjunction_scopes == ("BTC above 100000", "ETH above 5000")
        assert result.is_union is False
        assert result.union_scopes == ()


class TestMarketExtractorInit:
    """Tests for MarketExtractor initialization."""

    def test_creates_with_platform_and_key(self) -> None:
        """Test creating extractor with explicit API key."""
        extractor = MarketExtractor(platform="poly", api_key="sk-ant-test")
        assert extractor._platform == "poly"

    def test_raises_without_key(self) -> None:
        """Test that missing API key raises ValueError."""
        with patch("common.llm_extractor.client.load_api_key_from_env_file", return_value=None):
            with pytest.raises(ValueError):
                MarketExtractor(platform="poly")


class TestMarketExtractorBatch:
    """Tests for MarketExtractor.extract_batch."""

    @pytest.mark.asyncio
    async def test_returns_cached_when_all_cached(self) -> None:
        """Test that cached results are returned without API calls."""
        extractor = MarketExtractor(platform="poly", api_key="sk-ant-test")
        markets = [{"id": "cond-1", "title": "BTC above 100k"}]

        cached_data = {
            b"category": b"Crypto",
            b"underlying": b"BTC",
            b"subject": b"BTC",
            b"entity": b"BTC price",
            b"scope": b"above 100000",
            b"platform": b"poly",
            b"is_conjunction": b"False",
            b"is_union": b"False",
        }

        mock_redis = AsyncMock()
        mock_redis.hgetall = AsyncMock(return_value=cached_data)

        results = await extractor.extract_batch(markets, mock_redis)
        assert len(results) == 1
        assert results[0].market_id == "cond-1"
        assert results[0].category == "Crypto"

    @pytest.mark.asyncio
    async def test_calls_api_for_uncached_markets(self) -> None:
        """Test that API is called for markets not in cache."""
        extractor = MarketExtractor(platform="poly", api_key="sk-ant-test")
        markets = [{"id": "cond-new", "title": "ETH above 5k"}]

        mock_redis = AsyncMock()
        mock_redis.hgetall = AsyncMock(return_value={})
        mock_pipe = MagicMock()
        mock_pipe.hset = MagicMock(return_value=mock_pipe)
        mock_pipe.expire = MagicMock(return_value=mock_pipe)
        mock_pipe.execute = AsyncMock(return_value=[])
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)

        api_response = json.dumps(
            {
                "markets": [
                    {
                        "id": "cond-new",
                        "category": "Crypto",
                        "underlying": "ETH",
                        "subject": "ETH",
                        "entity": "ETH price",
                        "scope": "above 5000",
                        "floor_strike": 5000,
                        "cap_strike": None,
                        "is_conjunction": False,
                        "conjunction_scopes": [],
                        "is_union": False,
                        "union_scopes": [],
                    }
                ]
            }
        )

        with patch.object(extractor._client, "send_message", new_callable=AsyncMock, return_value=api_response):
            results = await extractor.extract_batch(markets, mock_redis)

        assert len(results) == 1
        assert results[0].market_id == "cond-new"
        assert results[0].underlying == "ETH"
        assert results[0].floor_strike == 5000.0
