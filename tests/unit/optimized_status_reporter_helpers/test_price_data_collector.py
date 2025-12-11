"""Unit tests for price_data_collector."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from common.optimized_status_reporter_helpers.price_data_collector import (
    PriceDataCollector,
)


class TestPriceDataCollector:
    """Tests for PriceDataCollector."""

    @pytest.fixture
    def collector(self):
        """PriceDataCollector instance."""
        return PriceDataCollector(redis_client=Mock())

    @pytest.mark.asyncio
    async def test_collect_price_data_success(self, collector):
        """Test successful collection of both BTC and ETH prices."""
        with patch("common.redis_protocol.market_store.DeribitStore") as mock_deribit_store:
            mock_store_instance = mock_deribit_store.return_value
            mock_store_instance.get_usdc_micro_price = AsyncMock(side_effect=[70000.0, 4000.0])

            result = await collector.collect_price_data()

            mock_store_instance.get_usdc_micro_price.assert_any_call("BTC")
            mock_store_instance.get_usdc_micro_price.assert_any_call("ETH")
            assert result == {"btc_price": 70000.0, "eth_price": 4000.0}

    @pytest.mark.asyncio
    async def test_collect_price_data_btc_failure(self, collector):
        """Test BTC price collection fails."""
        with patch("common.redis_protocol.market_store.DeribitStore") as mock_deribit_store:
            mock_store_instance = mock_deribit_store.return_value
            mock_store_instance.get_usdc_micro_price = AsyncMock(side_effect=[Exception("BTC error"), 4000.0])

            result = await collector.collect_price_data()

            assert result == {"btc_price": None, "eth_price": 4000.0}

    @pytest.mark.asyncio
    async def test_collect_price_data_eth_failure(self, collector):
        """Test ETH price collection fails."""
        with patch("common.redis_protocol.market_store.DeribitStore") as mock_deribit_store:
            mock_store_instance = mock_deribit_store.return_value
            mock_store_instance.get_usdc_micro_price = AsyncMock(side_effect=[70000.0, Exception("ETH error")])

            result = await collector.collect_price_data()

            assert result == {"btc_price": 70000.0, "eth_price": None}

    @pytest.mark.asyncio
    async def test_collect_price_data_both_failure(self, collector):
        """Test both BTC and ETH price collection fail."""
        with patch("common.redis_protocol.market_store.DeribitStore") as mock_deribit_store:
            mock_store_instance = mock_deribit_store.return_value
            mock_store_instance.get_usdc_micro_price = AsyncMock(side_effect=[Exception("BTC error"), Exception("ETH error")])

            result = await collector.collect_price_data()

            assert result == {"btc_price": None, "eth_price": None}

    @pytest.mark.asyncio
    async def test_collect_price_data_no_redis_client(self):
        """Test collector handles missing redis client (DeribitStore init)."""
        # DeribitStore will be instantiated with None, which might raise an error or behave differently.
        # We assume DeribitStore handles it, or its methods would fail.
        # If DeribitStore itself raises an error on init, that needs to be caught.

        collector = PriceDataCollector(redis_client=None)

        with patch("common.redis_protocol.market_store.DeribitStore") as mock_deribit_store:
            # If DeribitStore init itself fails, the constructor needs to be mocked.
            # Here, we assume the instantiation works, but calls to get_usdc_micro_price might fail.
            mock_store_instance = mock_deribit_store.return_value
            mock_store_instance.get_usdc_micro_price = AsyncMock(
                side_effect=[TypeError("Redis client required"), TypeError("Redis client required")]
            )

            result = await collector.collect_price_data()
            assert result == {"btc_price": None, "eth_price": None}
