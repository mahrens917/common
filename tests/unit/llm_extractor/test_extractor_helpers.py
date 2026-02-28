"""Tests for llm_extractor extractor helpers module."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.llm_extractor._extractor_helpers import (
    extract_kalshi_batch_with_retry,
    extract_kalshi_single,
    extract_poly_batch_with_retry,
    extract_poly_single_with_retry,
    get_batch_size,
    get_concurrent_requests,
    get_min_underlyings_for_dedup,
    get_redis_key,
    get_ttl,
    load_kalshi_cached,
    load_poly_cached_batch,
    store_kalshi_cached_batch,
    store_poly_cached_batch,
    store_poly_no_match_batch,
)
from common.llm_extractor.client import MessageResponse
from common.llm_extractor.models import MarketExtraction


def _msg(text: str) -> MessageResponse:
    """Create a MessageResponse with default token counts."""
    return MessageResponse(text=text, input_tokens=10, output_tokens=5)


class TestConstants:
    """Tests for constant getter functions."""

    def test_get_redis_key_kalshi(self) -> None:
        """Test Redis key format for Kalshi."""
        assert get_redis_key("m1", "kalshi") == "market:extracted:kalshi:m1"

    def test_get_redis_key_poly(self) -> None:
        """Test Redis key format for Poly."""
        assert get_redis_key("m1", "poly") == "market:extracted:poly:m1"

    def test_get_ttl(self) -> None:
        """Test TTL is 7 days."""
        assert get_ttl() == 604800

    def test_get_batch_size(self) -> None:
        """Test batch size."""
        assert get_batch_size() == 10

    def test_get_concurrent_requests(self) -> None:
        """Test concurrent requests limit."""
        assert get_concurrent_requests() == 5

    def test_get_min_underlyings_for_dedup(self) -> None:
        """Test minimum underlyings for dedup."""
        assert get_min_underlyings_for_dedup() == 2


class TestLoadKalshiCached:
    """Tests for load_kalshi_cached."""

    @pytest.mark.asyncio
    async def test_returns_cached_underlying(self) -> None:
        """Test returning cached underlying."""
        mock_redis = AsyncMock()
        mock_redis.hgetall = AsyncMock(return_value={"underlying": "BTC"})
        result = await load_kalshi_cached("m1", mock_redis)
        assert result == "BTC"

    @pytest.mark.asyncio
    async def test_returns_none_when_not_cached(self) -> None:
        """Test returning None when not cached."""
        mock_redis = AsyncMock()
        mock_redis.hgetall = AsyncMock(return_value={})
        result = await load_kalshi_cached("m1", mock_redis)
        assert result is None


class TestStoreKalshiCachedBatch:
    """Tests for store_kalshi_cached_batch."""

    @pytest.mark.asyncio
    async def test_stores_batch(self) -> None:
        """Test storing batch in Redis."""
        mock_pipe = MagicMock()
        mock_pipe.hset = MagicMock(return_value=mock_pipe)
        mock_pipe.expire = MagicMock(return_value=mock_pipe)
        mock_pipe.execute = AsyncMock()

        mock_redis = MagicMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)

        await store_kalshi_cached_batch({"m1": "BTC", "m2": "ETH"}, mock_redis)
        assert mock_pipe.hset.call_count == 2
        assert mock_pipe.expire.call_count == 2

    @pytest.mark.asyncio
    async def test_skips_empty_batch(self) -> None:
        """Test skipping empty batch."""
        mock_redis = MagicMock()
        await store_kalshi_cached_batch({}, mock_redis)
        mock_redis.pipeline.assert_not_called()


class TestExtractKalshiSingle:
    """Tests for extract_kalshi_single."""

    @pytest.mark.asyncio
    async def test_extracts_underlying(self) -> None:
        """Test extracting single underlying."""
        mock_client = AsyncMock()
        mock_client.send_message = AsyncMock(return_value=_msg('{"underlying": "BTC"}'))

        market = {"id": "m1", "title": "BTC above 100k", "category": "Crypto", "rules_primary": ""}
        result = await extract_kalshi_single(mock_client, market, ["ETH"])
        assert result == "BTC"


class TestExtractKalshiBatchWithRetry:
    """Tests for extract_kalshi_batch_with_retry."""

    @pytest.mark.asyncio
    async def test_extracts_batch(self) -> None:
        """Test extracting batch of underlyings."""
        mock_client = AsyncMock()
        mock_client.send_message = AsyncMock(return_value=_msg('{"markets": [{"id": "m1", "underlying": "BTC"}]}'))

        mock_pipe = MagicMock()
        mock_pipe.hset = MagicMock(return_value=mock_pipe)
        mock_pipe.expire = MagicMock(return_value=mock_pipe)
        mock_pipe.execute = AsyncMock()

        mock_redis = MagicMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)

        batch = [{"id": "m1", "title": "BTC above 100k", "category": "Crypto", "rules_primary": ""}]
        result = await extract_kalshi_batch_with_retry(mock_client, batch, [], mock_redis)
        assert result == {"m1": "BTC"}


class TestLoadPolyCachedBatch:
    """Tests for load_poly_cached_batch."""

    @pytest.mark.asyncio
    async def test_returns_cached_extractions(self) -> None:
        """Test returning cached extractions."""
        mock_redis = AsyncMock()
        mock_redis.hgetall = AsyncMock(return_value={"category": "Crypto", "underlying": "BTC", "strike_type": "greater"})

        markets = [{"id": "m1", "title": "BTC above 100k"}]
        cached, uncached = await load_poly_cached_batch(markets, mock_redis)
        assert len(cached) == 1
        assert cached[0].market_id == "m1"
        assert uncached == []

    @pytest.mark.asyncio
    async def test_returns_uncached_markets(self) -> None:
        """Test returning uncached markets."""
        mock_redis = AsyncMock()
        mock_redis.hgetall = AsyncMock(return_value={})

        markets = [{"id": "m1", "title": "BTC above 100k"}]
        cached, uncached = await load_poly_cached_batch(markets, mock_redis)
        assert cached == []
        assert len(uncached) == 1

    @pytest.mark.asyncio
    async def test_skips_no_match_cached(self) -> None:
        """Test skipping markets marked as no_match."""
        mock_redis = AsyncMock()
        mock_redis.hgetall = AsyncMock(return_value={"status": "no_match"})

        markets = [{"id": "m1", "title": "Some market"}]
        cached, uncached = await load_poly_cached_batch(markets, mock_redis)
        assert cached == []
        assert uncached == []


class TestStorePolyCachedBatch:
    """Tests for store_poly_cached_batch."""

    @pytest.mark.asyncio
    async def test_stores_extractions(self) -> None:
        """Test storing extractions in Redis."""
        mock_pipe = MagicMock()
        mock_pipe.hset = MagicMock(return_value=mock_pipe)
        mock_pipe.expire = MagicMock(return_value=mock_pipe)
        mock_pipe.execute = AsyncMock()

        mock_redis = MagicMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)

        extraction = MarketExtraction(
            market_id="m1",
            platform="poly",
            category="Crypto",
            underlying="BTC",
            strike_type="greater",
            floor_strike=100000.0,
            cap_strike=None,
            close_time=None,
        )
        await store_poly_cached_batch([extraction], mock_redis)
        mock_pipe.hset.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_empty_batch(self) -> None:
        """Test skipping empty batch."""
        mock_redis = MagicMock()
        await store_poly_cached_batch([], mock_redis)
        mock_redis.pipeline.assert_not_called()


class TestStorePolyNoMatchBatch:
    """Tests for store_poly_no_match_batch."""

    @pytest.mark.asyncio
    async def test_stores_no_match_markers(self) -> None:
        """Test storing no_match markers."""
        mock_pipe = MagicMock()
        mock_pipe.hset = MagicMock(return_value=mock_pipe)
        mock_pipe.expire = MagicMock(return_value=mock_pipe)
        mock_pipe.execute = AsyncMock()

        mock_redis = MagicMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)

        await store_poly_no_match_batch(["m1", "m2"], mock_redis)
        assert mock_pipe.hset.call_count == 2

    @pytest.mark.asyncio
    async def test_skips_empty_list(self) -> None:
        """Test skipping empty list."""
        mock_redis = MagicMock()
        await store_poly_no_match_batch([], mock_redis)
        mock_redis.pipeline.assert_not_called()


class TestExtractPolySingleWithRetry:
    """Tests for extract_poly_single_with_retry."""

    @pytest.mark.asyncio
    async def test_extracts_on_first_attempt(self) -> None:
        """Test successful extraction on first attempt."""
        mock_client = AsyncMock()
        mock_client.send_message = AsyncMock(
            return_value=_msg('{"category": "Crypto", "underlying": "BTC", "strike_type": "greater", "floor_strike": 100000}')
        )

        market = {"id": "m1", "title": "BTC above 100k", "description": "Will BTC go above 100k?"}
        result = await extract_poly_single_with_retry(mock_client, market, {"Crypto"}, {"BTC"})
        assert result is not None
        assert result.market_id == "m1"

    @pytest.mark.asyncio
    async def test_returns_none_on_invalid(self) -> None:
        """Test returning None on invalid extraction after retry."""
        mock_client = AsyncMock()
        mock_client.send_message = AsyncMock(return_value=_msg('{"category": "Invalid", "underlying": "BTC", "strike_type": "greater"}'))

        market = {"id": "m1", "title": "BTC above 100k", "description": "Will BTC go above 100k?"}
        result = await extract_poly_single_with_retry(mock_client, market, {"Crypto"}, {"BTC"})
        assert result is None


class TestExtractPolyBatchWithRetry:
    """Tests for extract_poly_batch_with_retry."""

    @pytest.mark.asyncio
    async def test_extracts_batch(self) -> None:
        """Test extracting batch of markets."""
        mock_client = AsyncMock()
        mock_client.send_message = AsyncMock(
            return_value=_msg(
                '{"markets": [{"id": "m1", "category": "Crypto", "underlying": "BTC", "strike_type": "greater", "floor_strike": 100000}]}'
            )
        )

        mock_pipe = MagicMock()
        mock_pipe.hset = MagicMock(return_value=mock_pipe)
        mock_pipe.expire = MagicMock(return_value=mock_pipe)
        mock_pipe.execute = AsyncMock()

        mock_redis = MagicMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)

        batch = [{"id": "m1", "title": "BTC above 100k"}]
        result = await extract_poly_batch_with_retry(mock_client, batch, {"Crypto"}, {"BTC"}, mock_redis)
        assert len(result) == 1
        assert result[0].market_id == "m1"
