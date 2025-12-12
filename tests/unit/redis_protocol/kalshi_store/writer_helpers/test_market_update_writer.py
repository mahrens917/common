"""Tests for market_update_writer module."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from common.redis_protocol.kalshi_store.writer_helpers.market_update_writer import (
    MarketDataMixin,
    RedisConnectionMixin,
)


class TestRedisConnectionMixin:
    """Tests for RedisConnectionMixin."""

    @pytest.mark.asyncio
    async def test_ensure_redis_uses_existing_connection(self):
        """Test _ensure_redis returns existing redis connection."""
        mixin = RedisConnectionMixin()
        mock_redis = MagicMock()
        mixin.redis = mock_redis
        mixin._connection_manager = None
        
        result = await mixin._ensure_redis()
        assert result is mock_redis

    @pytest.mark.asyncio
    async def test_ensure_redis_raises_when_no_connection(self):
        """Test _ensure_redis raises RuntimeError when redis is not initialized."""
        mixin = RedisConnectionMixin()
        mixin.redis = None
        mixin._connection_manager = None
        
        with pytest.raises(RuntimeError, match="Redis connection is not initialized"):
            await mixin._ensure_redis()


class TestMarketDataMixin:
    """Tests for MarketDataMixin error handling."""

    @pytest.mark.asyncio
    async def test_write_enhanced_market_data_requires_ticker(self):
        """Test write_enhanced_market_data raises TypeError when ticker is empty."""
        mixin = MarketDataMixin()
        mixin.redis = None
        mixin._connection_manager = None
        
        with pytest.raises(TypeError, match="market_ticker must be provided"):
            await mixin._write_enhanced_market_data("", "key", {"field": "value"})

    @pytest.mark.asyncio
    async def test_write_enhanced_market_data_requires_field_updates(self):
        """Test write_enhanced_market_data raises ValueError when field_updates is empty."""
        mixin = MarketDataMixin()
        mixin.redis = None
        mixin._connection_manager = None
        
        with pytest.raises(ValueError, match="field_updates must contain at least one field"):
            await mixin._write_enhanced_market_data("ticker", "key", {})
