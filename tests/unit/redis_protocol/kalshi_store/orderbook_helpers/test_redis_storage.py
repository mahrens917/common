"""Tests for snapshot_processor_helpers.redis_storage module."""

from unittest.mock import AsyncMock

import pytest

from common.redis_protocol.kalshi_store.orderbook_helpers.snapshot_processor_helpers.redis_storage import (
    store_best_prices,
    store_hash_fields,
)


@pytest.mark.asyncio
async def test_store_hash_fields_overwrites_timestamp() -> None:
    """store_hash_fields replaces any existing timestamp key with the given value."""
    redis = AsyncMock()
    hash_data = {"yes_bids": '{"50":3}', "timestamp": "old"}

    await store_hash_fields(redis, "market:TEST", hash_data, "new_ts")

    redis.hset.assert_awaited_once()
    mapping = redis.hset.call_args.kwargs["mapping"]
    assert mapping["timestamp"] == "new_ts"
    assert mapping["yes_bids"] == '{"50":3}'


@pytest.mark.asyncio
async def test_store_best_prices_sets_and_deletes() -> None:
    """store_best_prices sets non-None fields and deletes None fields."""
    redis = AsyncMock()

    await store_best_prices(redis, "market:TEST", 50, None, 10, None)

    redis.hset.assert_awaited_once()
    set_mapping = redis.hset.call_args.kwargs["mapping"]
    assert set_mapping == {"yes_bid": "50", "yes_bid_size": "10"}

    redis.hdel.assert_awaited_once()
    del_args = redis.hdel.call_args.args
    assert del_args == ("market:TEST", "yes_ask", "yes_ask_size")


@pytest.mark.asyncio
async def test_store_best_prices_all_present() -> None:
    """store_best_prices sets all fields when none are None."""
    redis = AsyncMock()

    await store_best_prices(redis, "market:TEST", 50, 55, 10, 20)

    redis.hset.assert_awaited_once()
    redis.hdel.assert_not_awaited()


@pytest.mark.asyncio
async def test_store_best_prices_all_none() -> None:
    """store_best_prices deletes all fields when all are None."""
    redis = AsyncMock()

    await store_best_prices(redis, "market:TEST", None, None, None, None)

    redis.hset.assert_not_awaited()
    redis.hdel.assert_awaited_once()
