"""Tests for event_publisher module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.redis_protocol.kalshi_store.orderbook_helpers.event_publisher import (
    clear_publisher_state,
    publish_market_event_throttled,
)


@pytest.fixture(autouse=True)
def _clear_state():
    """Clear publisher state before each test."""
    clear_publisher_state()
    yield
    clear_publisher_state()


class TestPublishMarketEventThrottled:
    """Tests for publish_market_event_throttled function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.hget = AsyncMock(return_value=b"KXHIGH-25DEC28")
        redis.publish = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_publishes_on_first_call(self, mock_redis):
        result = await publish_market_event_throttled(mock_redis, "market:key", "KXHIGH-25DEC28-B45", "2025-01-01T00:00:00Z")

        assert result is True
        mock_redis.publish.assert_called_once()
        channel = mock_redis.publish.call_args[0][0]
        assert channel == "market_event_updates:KXHIGH-25DEC28"

    @pytest.mark.asyncio
    async def test_throttles_rapid_calls(self, mock_redis):
        first = await publish_market_event_throttled(mock_redis, "market:key", "KXHIGH-25DEC28-B45", "2025-01-01T00:00:00Z")
        second = await publish_market_event_throttled(mock_redis, "market:key", "KXHIGH-25DEC28-B50", "2025-01-01T00:00:01Z")

        assert first is True
        assert second is False
        assert mock_redis.publish.call_count == 1

    @pytest.mark.asyncio
    async def test_different_events_not_throttled(self, mock_redis):
        mock_redis.hget = AsyncMock(side_effect=[b"EVENT-A", b"EVENT-B"])

        first = await publish_market_event_throttled(mock_redis, "market:key:a", "TICKER-A", "2025-01-01T00:00:00Z")
        second = await publish_market_event_throttled(mock_redis, "market:key:b", "TICKER-B", "2025-01-01T00:00:00Z")

        assert first is True
        assert second is True
        assert mock_redis.publish.call_count == 2

    @pytest.mark.asyncio
    async def test_skips_publish_when_no_event_ticker(self, mock_redis):
        mock_redis.hget = AsyncMock(return_value=None)

        result = await publish_market_event_throttled(mock_redis, "market:key", "TICKER", "2025-01-01T00:00:00Z")

        assert result is False
        mock_redis.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_string_event_ticker(self, mock_redis):
        mock_redis.hget = AsyncMock(return_value="STRING-EVENT")

        result = await publish_market_event_throttled(mock_redis, "market:key", "TICKER", "2025-01-01T00:00:00Z")

        assert result is True
        channel = mock_redis.publish.call_args[0][0]
        assert channel == "market_event_updates:STRING-EVENT"

    @pytest.mark.asyncio
    async def test_raises_on_connection_error(self, mock_redis):
        mock_redis.hget = AsyncMock(side_effect=ConnectionError("test"))

        with pytest.raises(ConnectionError, match="test"):
            await publish_market_event_throttled(mock_redis, "market:key", "TICKER", "2025-01-01T00:00:00Z")


class TestClearPublisherState:
    """Tests for clear_publisher_state function."""

    @pytest.mark.asyncio
    async def test_clears_throttle_state(self):
        mock_redis = MagicMock()
        mock_redis.hget = AsyncMock(return_value=b"EVENT-X")
        mock_redis.publish = AsyncMock()

        await publish_market_event_throttled(mock_redis, "market:key", "TICKER", "2025-01-01T00:00:00Z")
        assert mock_redis.publish.call_count == 1

        clear_publisher_state()

        await publish_market_event_throttled(mock_redis, "market:key", "TICKER", "2025-01-01T00:00:01Z")
        assert mock_redis.publish.call_count == 2
