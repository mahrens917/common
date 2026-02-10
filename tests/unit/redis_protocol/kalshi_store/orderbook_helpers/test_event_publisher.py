"""Tests for event_publisher module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.redis_protocol.kalshi_store.orderbook_helpers.event_publisher import (
    publish_market_event,
)


class TestPublishMarketEvent:
    """Tests for publish_market_event function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.hget = AsyncMock(return_value=b"KXHIGH-25DEC28")
        redis.xadd = AsyncMock(return_value=b"1-0")
        return redis

    @pytest.mark.asyncio
    async def test_publishes_event(self, mock_redis):
        result = await publish_market_event(mock_redis, "market:key", "KXHIGH-25DEC28-B45", "2025-01-01T00:00:00Z")

        assert result is True
        mock_redis.xadd.assert_called_once()

    @pytest.mark.asyncio
    async def test_publishes_every_call(self, mock_redis):
        first = await publish_market_event(mock_redis, "market:key", "KXHIGH-25DEC28-B45", "2025-01-01T00:00:00Z")
        second = await publish_market_event(mock_redis, "market:key", "KXHIGH-25DEC28-B50", "2025-01-01T00:00:01Z")

        assert first is True
        assert second is True
        assert mock_redis.xadd.call_count == 2

    @pytest.mark.asyncio
    async def test_skips_publish_when_no_event_ticker(self, mock_redis):
        mock_redis.hget = AsyncMock(return_value=None)

        result = await publish_market_event(mock_redis, "market:key", "TICKER", "2025-01-01T00:00:00Z")

        assert result is False
        mock_redis.xadd.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_string_event_ticker(self, mock_redis):
        mock_redis.hget = AsyncMock(return_value="STRING-EVENT")

        result = await publish_market_event(mock_redis, "market:key", "TICKER", "2025-01-01T00:00:00Z")

        assert result is True
        mock_redis.xadd.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_on_connection_error(self, mock_redis):
        mock_redis.hget = AsyncMock(side_effect=ConnectionError("test"))

        with pytest.raises(ConnectionError, match="test"):
            await publish_market_event(mock_redis, "market:key", "TICKER", "2025-01-01T00:00:00Z")
