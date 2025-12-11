"""Tests for KalshiMarketReaderAsyncMethodsMixin."""

import pytest

from common.redis_protocol.kalshi_store.reader_async_methods_mixin import (
    KalshiMarketReaderAsyncMethodsMixin,
)


class TestKalshiMarketReaderAsyncMethodsMixin:
    """Test the async methods mixin."""

    @pytest.mark.asyncio
    async def test_get_subscribed_markets_not_implemented(self):
        """Test that get_subscribed_markets raises NotImplementedError."""
        mixin = KalshiMarketReaderAsyncMethodsMixin()
        with pytest.raises(NotImplementedError):
            await mixin.get_subscribed_markets()

    @pytest.mark.asyncio
    async def test_is_market_tracked_not_implemented(self):
        """Test that is_market_tracked raises NotImplementedError."""
        mixin = KalshiMarketReaderAsyncMethodsMixin()
        with pytest.raises(NotImplementedError):
            await mixin.is_market_tracked("TEST-MARKET")

    @pytest.mark.asyncio
    async def test_get_markets_by_currency_not_implemented(self):
        """Test that get_markets_by_currency raises NotImplementedError."""
        mixin = KalshiMarketReaderAsyncMethodsMixin()
        with pytest.raises(NotImplementedError):
            await mixin.get_markets_by_currency("USD")

    @pytest.mark.asyncio
    async def test_get_active_strikes_and_expiries_not_implemented(self):
        """Test that get_active_strikes_and_expiries raises NotImplementedError."""
        mixin = KalshiMarketReaderAsyncMethodsMixin()
        with pytest.raises(NotImplementedError):
            await mixin.get_active_strikes_and_expiries("USD")

    @pytest.mark.asyncio
    async def test_get_market_data_for_strike_expiry_not_implemented(self):
        """Test that get_market_data_for_strike_expiry raises NotImplementedError."""
        mixin = KalshiMarketReaderAsyncMethodsMixin()
        with pytest.raises(NotImplementedError):
            await mixin.get_market_data_for_strike_expiry("USD", "2025-01-01", 100.0)

    @pytest.mark.asyncio
    async def test_is_market_expired_not_implemented(self):
        """Test that is_market_expired raises NotImplementedError."""
        mixin = KalshiMarketReaderAsyncMethodsMixin()
        with pytest.raises(NotImplementedError):
            await mixin.is_market_expired("TEST-MARKET")

    @pytest.mark.asyncio
    async def test_is_market_settled_not_implemented(self):
        """Test that is_market_settled raises NotImplementedError."""
        mixin = KalshiMarketReaderAsyncMethodsMixin()
        with pytest.raises(NotImplementedError):
            await mixin.is_market_settled("TEST-MARKET")

    @pytest.mark.asyncio
    async def test_get_market_snapshot_not_implemented(self):
        """Test that get_market_snapshot raises NotImplementedError."""
        mixin = KalshiMarketReaderAsyncMethodsMixin()
        with pytest.raises(NotImplementedError):
            await mixin.get_market_snapshot("TEST-MARKET")

    @pytest.mark.asyncio
    async def test_get_market_snapshot_by_key_not_implemented(self):
        """Test that get_market_snapshot_by_key raises NotImplementedError."""
        mixin = KalshiMarketReaderAsyncMethodsMixin()
        with pytest.raises(NotImplementedError):
            await mixin.get_market_snapshot_by_key("test:key")

    @pytest.mark.asyncio
    async def test_get_market_metadata_not_implemented(self):
        """Test that get_market_metadata raises NotImplementedError."""
        mixin = KalshiMarketReaderAsyncMethodsMixin()
        with pytest.raises(NotImplementedError):
            await mixin.get_market_metadata("TEST-MARKET")

    @pytest.mark.asyncio
    async def test_get_market_field_not_implemented(self):
        """Test that get_market_field raises NotImplementedError."""
        mixin = KalshiMarketReaderAsyncMethodsMixin()
        with pytest.raises(NotImplementedError):
            await mixin.get_market_field("TEST-MARKET", "field")

    @pytest.mark.asyncio
    async def test_get_orderbook_not_implemented(self):
        """Test that get_orderbook raises NotImplementedError."""
        mixin = KalshiMarketReaderAsyncMethodsMixin()
        with pytest.raises(NotImplementedError):
            await mixin.get_orderbook("TEST-MARKET")

    @pytest.mark.asyncio
    async def test_get_orderbook_side_not_implemented(self):
        """Test that get_orderbook_side raises NotImplementedError."""
        mixin = KalshiMarketReaderAsyncMethodsMixin()
        with pytest.raises(NotImplementedError):
            await mixin.get_orderbook_side("TEST-MARKET", "yes")

    @pytest.mark.asyncio
    async def test_scan_market_keys_not_implemented(self):
        """Test that scan_market_keys raises NotImplementedError."""
        mixin = KalshiMarketReaderAsyncMethodsMixin()
        with pytest.raises(NotImplementedError):
            await mixin.scan_market_keys()
