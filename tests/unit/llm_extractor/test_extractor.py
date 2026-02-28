"""Tests for llm_extractor extractor module."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.llm_extractor.client import MessageResponse
from common.llm_extractor.extractor import (
    ExpiryAligner,
    KalshiDedupExtractor,
    KalshiUnderlyingExtractor,
    PolyExtractor,
    get_redis_key,
    get_ttl,
)
from common.llm_extractor.models import MarketExtraction


def _msg(text: str) -> MessageResponse:
    """Create a MessageResponse with default token counts."""
    return MessageResponse(text=text, input_tokens=10, output_tokens=5)


class TestGetRedisKey:
    """Tests for get_redis_key."""

    def test_kalshi_key_format(self) -> None:
        """Test Redis key format for Kalshi markets."""
        assert get_redis_key("KXETHD-26JAN", "kalshi") == "market:extracted:kalshi:KXETHD-26JAN"

    def test_poly_key_format(self) -> None:
        """Test Redis key format for Poly markets."""
        assert get_redis_key("cond-123", "poly") == "market:extracted:poly:cond-123"


class TestGetTtl:
    """Tests for get_ttl."""

    def test_returns_7_days(self) -> None:
        """Test that TTL is 7 days."""
        assert get_ttl() == 604800


class TestKalshiUnderlyingExtractorInit:
    """Tests for KalshiUnderlyingExtractor initialization."""

    def test_creates_with_api_key(self) -> None:
        """Test creating extractor with explicit API key."""
        extractor = KalshiUnderlyingExtractor(api_key="sk-ant-test")
        assert extractor.client is not None

    def test_raises_without_key(self) -> None:
        """Test that missing API key raises ValueError."""
        with patch("common.llm_extractor.client.load_api_key_from_env_file", return_value=None):
            with pytest.raises(ValueError):
                KalshiUnderlyingExtractor()


class TestKalshiUnderlyingExtractor:
    """Tests for KalshiUnderlyingExtractor.extract_underlyings."""

    @pytest.mark.asyncio
    async def test_returns_cached_when_all_cached(self) -> None:
        """Test that cached results are returned without API calls."""
        extractor = KalshiUnderlyingExtractor(api_key="sk-ant-test")
        markets = [{"id": "m1", "title": "BTC above 100k", "category": "Crypto", "rules_primary": ""}]

        mock_redis = AsyncMock()
        mock_redis.hgetall = AsyncMock(return_value={"underlying": "BTC"})

        results = await extractor.extract_underlyings(markets, mock_redis)
        assert results == {"m1": "BTC"}

    @pytest.mark.asyncio
    async def test_calls_api_for_uncached_markets(self) -> None:
        """Test that API is called for markets not in cache."""
        extractor = KalshiUnderlyingExtractor(api_key="sk-ant-test")
        markets = [{"id": "m1", "title": "ETH above 5k", "category": "Crypto", "rules_primary": ""}]

        mock_redis = AsyncMock()
        mock_redis.hgetall = AsyncMock(return_value={})
        mock_pipe = MagicMock()
        mock_pipe.hset = MagicMock(return_value=mock_pipe)
        mock_pipe.expire = MagicMock(return_value=mock_pipe)
        mock_pipe.execute = AsyncMock(return_value=[])
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)

        # Batch response format
        api_response = _msg(json.dumps({"markets": [{"id": "m1", "underlying": "ETH"}]}))

        with patch.object(extractor._client, "send_message", new_callable=AsyncMock, return_value=api_response):
            results = await extractor.extract_underlyings(markets, mock_redis)

        assert results == {"m1": "ETH"}
        mock_pipe.hset.assert_called_once()


class TestKalshiDedupExtractorInit:
    """Tests for KalshiDedupExtractor initialization."""

    def test_creates_with_api_key(self) -> None:
        """Test creating extractor with explicit API key."""
        extractor = KalshiDedupExtractor(api_key="sk-ant-test")
        assert extractor.client is not None


class TestKalshiDedupExtractor:
    """Tests for KalshiDedupExtractor.dedup_underlyings."""

    @pytest.mark.asyncio
    async def test_returns_cached_when_cached(self) -> None:
        """Test that cached dedup results are returned."""
        extractor = KalshiDedupExtractor(api_key="sk-ant-test")
        underlyings_by_category = {"Crypto": {"BTC", "BITCOIN", "ETH"}}

        cached_mapping = json.dumps({"BITCOIN": "BTC"})
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=cached_mapping)

        results = await extractor.dedup_underlyings(underlyings_by_category, mock_redis)
        assert results == {"BITCOIN": "BTC"}

    @pytest.mark.asyncio
    async def test_calls_api_for_uncached(self) -> None:
        """Test that API is called when not cached."""
        extractor = KalshiDedupExtractor(api_key="sk-ant-test")
        underlyings_by_category = {"Crypto": {"BTC", "BITCOIN"}}

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock()

        api_response = _msg(json.dumps({"groups": [{"canonical": "BTC", "aliases": ["BITCOIN"]}]}))

        with patch.object(extractor._client, "send_message", new_callable=AsyncMock, return_value=api_response):
            results = await extractor.dedup_underlyings(underlyings_by_category, mock_redis)

        assert results == {"BITCOIN": "BTC"}

    @pytest.mark.asyncio
    async def test_skips_single_underlying_categories(self) -> None:
        """Test that categories with only one underlying are skipped."""
        extractor = KalshiDedupExtractor(api_key="sk-ant-test")
        underlyings_by_category = {"Crypto": {"BTC"}}  # Only one, no dedup needed

        mock_redis = AsyncMock()

        with patch.object(extractor._client, "send_message", new_callable=AsyncMock) as mock_send:
            results = await extractor.dedup_underlyings(underlyings_by_category, mock_redis)

        assert results == {}
        mock_send.assert_not_called()


class TestPolyExtractorInit:
    """Tests for PolyExtractor initialization."""

    def test_creates_with_api_key(self) -> None:
        """Test creating extractor with explicit API key."""
        extractor = PolyExtractor(api_key="sk-ant-test")
        assert extractor.client is not None


class TestPolyExtractor:
    """Tests for PolyExtractor.extract_batch."""

    @pytest.mark.asyncio
    async def test_returns_cached_when_all_cached(self) -> None:
        """Test that cached results are returned without API calls."""
        extractor = PolyExtractor(api_key="sk-ant-test")
        markets = [{"id": "cond-1", "title": "BTC above 100k"}]

        cached_data = {
            "category": "Crypto",
            "underlying": "BTC",
            "strike_type": "greater",
            "floor_strike": "100000.0",
        }

        mock_redis = AsyncMock()
        mock_redis.hgetall = AsyncMock(return_value=cached_data)

        results = await extractor.extract_batch(markets, {"Crypto"}, {"BTC"}, mock_redis)
        assert len(results) == 1
        assert results[0].market_id == "cond-1"
        assert results[0].category == "Crypto"

    @pytest.mark.asyncio
    async def test_calls_api_for_uncached_markets(self) -> None:
        """Test that API is called for markets not in cache."""
        extractor = PolyExtractor(api_key="sk-ant-test")
        markets = [{"id": "cond-new", "title": "ETH above 5k"}]

        mock_redis = AsyncMock()
        mock_redis.hgetall = AsyncMock(return_value={})
        mock_pipe = MagicMock()
        mock_pipe.hset = MagicMock(return_value=mock_pipe)
        mock_pipe.expire = MagicMock(return_value=mock_pipe)
        mock_pipe.execute = AsyncMock(return_value=[])
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)

        api_response = _msg(
            json.dumps(
                {
                    "markets": [
                        {
                            "id": "cond-new",
                            "category": "Crypto",
                            "underlying": "ETH",
                            "strike_type": "greater",
                            "floor_strike": 5000,
                            "cap_strike": None,
                        }
                    ]
                }
            )
        )

        with patch.object(extractor._client, "send_message", new_callable=AsyncMock, return_value=api_response):
            results = await extractor.extract_batch(markets, {"Crypto"}, {"ETH"}, mock_redis)

        assert len(results) == 1
        assert results[0].market_id == "cond-new"
        assert results[0].underlying == "ETH"
        assert results[0].floor_strike == 5000.0

    @pytest.mark.asyncio
    async def test_retries_failed_extractions(self) -> None:
        """Test that failed extractions are retried individually."""
        extractor = PolyExtractor(api_key="sk-ant-test")
        markets = [{"id": "m1", "title": "BTC above 100k", "description": "Will BTC go above 100k?"}]

        mock_redis = AsyncMock()
        mock_redis.hgetall = AsyncMock(return_value={})
        mock_pipe = MagicMock()
        mock_pipe.hset = MagicMock(return_value=mock_pipe)
        mock_pipe.expire = MagicMock(return_value=mock_pipe)
        mock_pipe.execute = AsyncMock(return_value=[])
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)

        # First call returns invalid, retry returns valid
        invalid_response = _msg(
            json.dumps(
                {
                    "markets": [
                        {
                            "id": "m1",
                            "category": "Invalid",  # Invalid category
                            "underlying": "BTC",
                            "strike_type": "greater",
                        }
                    ]
                }
            )
        )
        valid_response = _msg(
            json.dumps(
                {
                    "category": "Crypto",
                    "underlying": "BTC",
                    "strike_type": "greater",
                    "floor_strike": 100000,
                    "cap_strike": None,
                }
            )
        )

        call_count = 0

        async def mock_send(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return invalid_response
            return valid_response

        with patch.object(extractor._client, "send_message", side_effect=mock_send):
            results = await extractor.extract_batch(markets, {"Crypto"}, {"BTC"}, mock_redis)

        # Should have retried and succeeded
        assert len(results) == 1
        assert results[0].category == "Crypto"


class TestExpiryAlignerInit:
    """Tests for ExpiryAligner initialization."""

    def test_creates_with_redis(self) -> None:
        """Test creating aligner with Redis connection."""
        mock_redis = AsyncMock()
        aligner = ExpiryAligner(redis=mock_redis)
        assert aligner.client is not None


class TestExpiryAligner:
    """Tests for ExpiryAligner."""

    @pytest.mark.asyncio
    async def test_returns_cached_alignment(self) -> None:
        """Test that cached alignment results are returned."""
        mock_redis = AsyncMock()
        mock_redis.hgetall = AsyncMock(return_value={"aligned_expiry": "2024-01-15"})

        aligner = ExpiryAligner(redis=mock_redis)

        result = await aligner.align_expiry(
            kalshi_id="k1",
            kalshi_title="BTC above 100k by Jan 15",
            kalshi_expiry="2024-01-15T00:00:00Z",
            poly_id="p1",
            poly_title="Bitcoin over 100k",
            poly_expiry="2024-01-14T23:00:00Z",
        )
        assert result == "2024-01-15"

    @pytest.mark.asyncio
    async def test_returns_none_for_no_match_cached(self) -> None:
        """Test that None is returned when no_match is cached."""
        mock_redis = AsyncMock()
        mock_redis.hgetall = AsyncMock(return_value={"status": "no_match"})

        aligner = ExpiryAligner(redis=mock_redis)

        result = await aligner.align_expiry(
            kalshi_id="k1",
            kalshi_title="BTC event",
            kalshi_expiry="2024-01-15T00:00:00Z",
            poly_id="p1",
            poly_title="Different event",
            poly_expiry="2024-02-15T00:00:00Z",
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_calls_api_for_uncached(self) -> None:
        """Test that API is called when not cached."""
        mock_redis = AsyncMock()
        mock_redis.hgetall = AsyncMock(return_value={})
        mock_redis.hset = AsyncMock()
        mock_redis.expire = AsyncMock()

        aligner = ExpiryAligner(redis=mock_redis)

        api_response = _msg(json.dumps({"same_event": True, "event_date": "2024-01-15"}))

        with patch.object(aligner._client, "send_message", new_callable=AsyncMock, return_value=api_response):
            result = await aligner.align_expiry(
                kalshi_id="k1",
                kalshi_title="BTC above 100k by Jan 15",
                kalshi_expiry="2024-01-15T00:00:00Z",
                poly_id="p1",
                poly_title="Bitcoin over 100k",
                poly_expiry="2024-01-14T23:00:00Z",
            )

        assert result == "2024-01-15"

    @pytest.mark.asyncio
    async def test_stores_no_match_when_different_events(self) -> None:
        """Test that no_match is stored when events are different."""
        mock_redis = AsyncMock()
        mock_redis.hgetall = AsyncMock(return_value={})
        mock_redis.hset = AsyncMock()
        mock_redis.expire = AsyncMock()

        aligner = ExpiryAligner(redis=mock_redis)

        api_response = _msg(json.dumps({"same_event": False}))

        with patch.object(aligner._client, "send_message", new_callable=AsyncMock, return_value=api_response):
            result = await aligner.align_expiry(
                kalshi_id="k1",
                kalshi_title="BTC event",
                kalshi_expiry="2024-01-15T00:00:00Z",
                poly_id="p1",
                poly_title="ETH event",
                poly_expiry="2024-02-15T00:00:00Z",
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_align_batch(self) -> None:
        """Test batch alignment of multiple pairs."""
        mock_redis = AsyncMock()
        mock_redis.hgetall = AsyncMock(return_value={"aligned_expiry": "2024-01-15"})

        aligner = ExpiryAligner(redis=mock_redis)

        pairs = [
            ("k1", "BTC event", "2024-01-15T00:00:00Z", "p1", "BTC event", "2024-01-14T23:00:00Z", {"underlying": "BTC"}),
            ("k2", "ETH event", "2024-02-15T00:00:00Z", "p2", "ETH event", "2024-02-14T23:00:00Z", {"underlying": "ETH"}),
        ]

        results = await aligner.align_batch(pairs)
        assert len(results) == 2
        assert results[0] == "2024-01-15"
        assert results[1] == "2024-01-15"
