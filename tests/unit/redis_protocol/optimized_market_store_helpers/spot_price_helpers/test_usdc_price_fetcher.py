from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest
import redis.exceptions

from common.redis_protocol.atomic_redis_operations_helpers.data_fetcher import (
    RedisDataValidationError,
)
from common.redis_protocol.optimized_market_store_helpers.spot_price_helpers.usdc_price_fetcher import (
    UsdcPriceFetcher,
)


@pytest.fixture
def market_data_retriever():
    return AsyncMock()


@pytest.fixture
def price_calculator():
    return Mock()


@pytest.fixture
def fetcher(market_data_retriever, price_calculator):
    return UsdcPriceFetcher(market_data_retriever, price_calculator)


@pytest.mark.asyncio
async def test_get_usdc_bid_ask_prices_success(fetcher, market_data_retriever, price_calculator):
    market_data_retriever.get_usdc_market_data = AsyncMock(return_value={"best_bid": "100.5", "best_ask": "101.0"})
    price_calculator.extract_bid_ask_prices.return_value = (100.5, 101.0)

    result = await fetcher.get_usdc_bid_ask_prices("BTC")

    assert result == (100.5, 101.0)
    market_data_retriever.get_usdc_market_data.assert_called_once_with("BTC", None)
    price_calculator.extract_bid_ask_prices.assert_called_once()


@pytest.mark.asyncio
async def test_get_usdc_bid_ask_prices_with_atomic_ops(fetcher, market_data_retriever, price_calculator):
    market_data_retriever.get_usdc_market_data = AsyncMock(return_value={"best_bid": "100.5", "best_ask": "101.0"})
    price_calculator.extract_bid_ask_prices.return_value = (100.5, 101.0)
    atomic_ops = AsyncMock()

    result = await fetcher.get_usdc_bid_ask_prices("ETH", atomic_ops=atomic_ops)

    assert result == (100.5, 101.0)
    market_data_retriever.get_usdc_market_data.assert_called_once_with("ETH", atomic_ops)


@pytest.mark.asyncio
async def test_get_usdc_bid_ask_prices_value_error_from_validation(fetcher, market_data_retriever, price_calculator):
    market_data_retriever.get_usdc_market_data = AsyncMock(return_value={"best_bid": "-1", "best_ask": "101.0"})
    price_calculator.extract_bid_ask_prices.return_value = (-1, 101.0)

    with pytest.raises(ValueError, match="Invalid bid price"):
        await fetcher.get_usdc_bid_ask_prices("BTC")


@pytest.mark.asyncio
async def test_get_usdc_bid_ask_prices_redis_data_validation_error(fetcher, market_data_retriever, price_calculator):
    market_data_retriever.get_usdc_market_data = AsyncMock(side_effect=RedisDataValidationError("No data for key"))

    with pytest.raises(RedisDataValidationError):
        await fetcher.get_usdc_bid_ask_prices("BTC")


@pytest.mark.asyncio
async def test_get_usdc_bid_ask_prices_redis_error(fetcher, market_data_retriever, price_calculator):
    market_data_retriever.get_usdc_market_data = AsyncMock(side_effect=redis.exceptions.RedisError("Connection failed"))

    with pytest.raises(redis.exceptions.RedisError):
        await fetcher.get_usdc_bid_ask_prices("BTC")
