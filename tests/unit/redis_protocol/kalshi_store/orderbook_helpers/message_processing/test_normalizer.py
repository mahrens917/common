"""Tests for the orderbook JSON normalizer."""

from unittest.mock import AsyncMock, MagicMock

import orjson
import pytest

from src.common.redis_protocol.kalshi_store.orderbook_helpers.message_processing.normalizer import (
    normalize_price_map,
    normalize_snapshot_json,
)


def test_normalize_price_map_formats_keys_and_values():
    data = {
        "2": "2.5",
        3.0: "3",
        3.5: "4",
        True: "5",
        "bad": "value",
    }

    normalized = normalize_price_map(data)

    assert normalized["2"] == pytest.approx(2.5)
    assert normalized["3"] == pytest.approx(3.0)
    assert normalized["3.5"] == pytest.approx(4.0)
    assert normalized["1.0"] == pytest.approx(5.0)
    assert normalized["bad"] == "value"


@pytest.mark.asyncio
async def test_normalize_snapshot_updates_when_data_changes():
    redis = MagicMock()
    snapshot = {"1.0": "5", "2": "6"}
    redis.hget = AsyncMock(side_effect=[orjson.dumps(snapshot), None])
    redis.hset = AsyncMock()

    await normalize_snapshot_json(redis, "market")

    assert redis.hset.await_count == 1
    args, _ = redis.hset.await_args
    assert args[0] == "market"
    assert args[1] == "yes_bids"
    dumped = args[2]
    loaded = orjson.loads(dumped.encode() if isinstance(dumped, str) else dumped)
    assert loaded == {"1.0": 5.0, "2": 6.0}


@pytest.mark.asyncio
async def test_normalize_snapshot_skips_invalid_json():
    redis = MagicMock()
    redis.hget = AsyncMock(return_value=b"not-json")
    redis.hset = AsyncMock()

    await normalize_snapshot_json(redis, "market")

    assert redis.hset.await_count == 0
