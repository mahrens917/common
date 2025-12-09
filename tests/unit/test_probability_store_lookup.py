from unittest.mock import AsyncMock

import orjson
import pytest

from src.common.redis_protocol.probability_store import (
    ProbabilityDataNotFoundError,
    ProbabilityStore,
)

_VAL_0_4 = 0.4
_VAL_0_6 = 0.6


class _RedisStub:
    def __init__(self):
        self._data = {}
        self.hgetall = AsyncMock(side_effect=self._hgetall)
        self.hget = AsyncMock(side_effect=self._hget)

    async def _hgetall(self, key):
        return self._data.get(key, {}).copy()

    async def _hget(self, key, field):
        return self._data.get(key, {}).get(field)

    def set_hash(self, key, mapping):
        self._data[key] = mapping


@pytest.mark.asyncio
async def test_get_event_ticker_for_key_returns_value():
    redis = _RedisStub()
    redis.set_hash(
        "probabilities:BTC:2024-12-31:call:40000",
        {"event_ticker": "BTC-2024-12-31-CALL"},
    )

    store = ProbabilityStore(redis=redis)  # type: ignore[arg-type]
    ticker = await store.get_event_ticker_for_key("BTC:2024-12-31:40000:call")

    assert ticker == "BTC-2024-12-31-CALL"
    redis.hgetall.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_event_ticker_for_key_raises_when_missing():
    redis = _RedisStub()
    store = ProbabilityStore(redis=redis)  # type: ignore[arg-type]

    with pytest.raises(ProbabilityDataNotFoundError):
        await store.get_event_ticker_for_key("BTC:2024-12-31:40000:call")
    redis.hgetall.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_probabilities_groups_strikes_by_expiry():
    redis = _RedisStub()
    redis.set_hash(
        "probabilities:BTC",
        {
            "2024-12-31T00:00:00Z:40000": orjson.dumps({"probability": 0.6}).decode(),
            "2024-12-31T00:00:00Z:41000": orjson.dumps({"probability": 0.4}).decode(),
        },
    )

    store = ProbabilityStore(redis=redis)  # type: ignore[arg-type]
    result = await store.get_probabilities("BTC")

    assert "2024-12-31T00:00:00Z" in result
    strikes = result["2024-12-31T00:00:00Z"]
    assert "40000" in strikes and strikes["40000"]["probability"] == _VAL_0_6
    assert "41000" in strikes and strikes["41000"]["probability"] == _VAL_0_4
