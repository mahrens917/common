from decimal import Decimal
from typing import Any, Dict
from unittest.mock import AsyncMock

import pytest

from src.common.redis_protocol.probability_store import (
    ProbabilityData,
    ProbabilityDataNotFoundError,
    ProbabilityStore,
    ProbabilityStoreError,
    run_direct_connectivity_test,
    verify_probability_storage,
)


class PipelineStub:
    def __init__(self):
        self.commands: list[tuple[str, Any]] = []
        self.executed = False

    def delete(self, key: str):
        self.commands.append(("delete", key))
        return self

    def hset(self, key: str, field: str, value: str):
        self.commands.append(("hset", key, field, value))
        return self

    async def execute(self):
        self.executed = True
        results = []
        for command in self.commands:
            if command[0] == "delete":
                results.append(0)
            elif command[0] == "hset":
                results.append(1)
            else:
                results.append(0)
        return results


@pytest.fixture
def redis_mock():
    redis = AsyncMock()
    return redis


@pytest.mark.asyncio
async def test_store_probability_serializes_nan_and_range(redis_mock):
    store = ProbabilityStore(redis=redis_mock)

    data = ProbabilityData(
        currency="btc",
        expiry="2024-05-01",
        strike_type="greater",
        strike=100.4,
        probability=0.8,
        error=float("nan"),
        confidence=0.9,
        probability_range=(Decimal("0.1"), None),
    )
    await store.store_probability(data)

    redis_mock.hset.assert_awaited_once()
    key = redis_mock.hset.await_args.args[0]
    mapping = redis_mock.hset.await_args.kwargs["mapping"]

    assert key == "probabilities:BTC:2024-05-01:greater:100"
    assert mapping["probability"] == "0.8"
    assert mapping["error"] == "NaN"
    assert mapping["confidence"] == "0.9"
    assert mapping["range_low"] == "0.1"
    assert mapping["range_high"] == "null"


@pytest.mark.asyncio
async def test_store_probability_raises_when_no_fields(redis_mock):
    store = ProbabilityStore(redis=redis_mock)

    with pytest.raises((ProbabilityStoreError, TypeError)):
        # Creating ProbabilityData with None probability should fail
        data = ProbabilityData(
            currency="btc",
            expiry="2024-05-01",
            strike_type="greater",
            strike=100,
            probability=None,
        )
        await store.store_probability(data)

    redis_mock.hset.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_probability_data_converts_values(redis_mock):
    redis_mock.hgetall.return_value = {
        b"probability": b"0.5",
        b"confidence": b"NaN",
        b"note": b"sample",
    }
    store = ProbabilityStore(redis=redis_mock)

    result = await store.get_probability_data("btc", "2024-05-01", "100", "greater")

    assert result["probability"] == pytest.approx(0.5)
    assert result["confidence"] == "NaN"
    assert result["note"] == "sample"


@pytest.mark.asyncio
async def test_get_event_ticker_for_key_validates_pattern(redis_mock):
    store = ProbabilityStore(redis=redis_mock)

    with pytest.raises(ProbabilityStoreError):
        await store.get_event_ticker_for_key("BTC")
    redis_mock.hgetall.assert_not_awaited()

    redis_mock.hgetall.reset_mock()
    redis_mock.hgetall.return_value = {b"event_ticker": b"EVT-1"}
    ticker = await store.get_event_ticker_for_key("BTC:2024-05-01:100:greater")
    assert ticker == "EVT-1"


@pytest.mark.asyncio
async def test_store_probabilities_serializes_decimal(redis_mock):
    pipeline = PipelineStub()
    redis_mock.pipeline.return_value = pipeline
    redis_mock.hlen.return_value = 1

    probabilities: Dict[str, Dict[str, Dict[str, Any]]] = {
        "2024-05-01T00:00:00Z": {"100": {"probability": 0.4, "confidence": Decimal("0.75")}}
    }
    store = ProbabilityStore(redis=redis_mock)

    await store.store_probabilities("btc", probabilities)

    assert pipeline.executed is True
    assert ("delete", "probabilities:BTC") in pipeline.commands

    hset_calls = [cmd for cmd in pipeline.commands if cmd[0] == "hset"]
    assert len(hset_calls) == 1
    _, key, field, value = hset_calls[0]
    assert key == "probabilities:BTC"
    assert field == "2024-05-01T00:00:00Z:100"
    assert '"confidence":0.75' in value
    assert '"probability":0.4' in value


@pytest.mark.asyncio
async def test_get_probabilities_parses_and_sorts(redis_mock):
    redis_mock.hgetall.return_value = {
        "2024-05-01T00:00:00Z:100": b'{"probability": 0.7, "confidence": 0.5}',
        "2024-05-02T00:00:00+00:00:>1000": b'{"probability": 0.6}',
    }
    store = ProbabilityStore(redis=redis_mock)

    result = await store.get_probabilities("btc")

    assert "2024-05-01T00:00:00Z" in result
    assert result["2024-05-01T00:00:00Z"]["100"]["probability"] == pytest.approx(0.7)
    assert result["2024-05-01T00:00:00Z"]["100"]["confidence"] == pytest.approx(0.5)
    assert result["2024-05-02T00:00:00+00:00"][">1000"]["probability"] == pytest.approx(0.6)


@pytest.mark.asyncio
async def test_get_probability_data_handles_missing(redis_mock):
    redis_mock.hgetall.return_value = {}
    store = ProbabilityStore(redis=redis_mock)

    with pytest.raises(ProbabilityDataNotFoundError):
        await store.get_probability_data("btc", "2024-05-01", "100", "between")


@pytest.mark.asyncio
async def test_get_probabilities_raises_for_invalid_field(redis_mock):
    redis_mock.hgetall.return_value = {
        "invalid": b'{"probability": 0.5}',
    }
    store = ProbabilityStore(redis=redis_mock)

    with pytest.raises(ProbabilityStoreError, match="Invalid probability field format"):
        await store.get_probabilities("btc")


@pytest.mark.asyncio
async def test_get_probabilities_raises_for_bad_json(redis_mock):
    redis_mock.hgetall.return_value = {
        "2024-05-01T00:00:00Z:100": b"not-json",
    }
    store = ProbabilityStore(redis=redis_mock)

    with pytest.raises(ProbabilityStoreError, match="Error parsing probability payload"):
        await store.get_probabilities("btc")


@pytest.mark.asyncio
async def test_verify_probability_storage_runs_connectivity(monkeypatch):
    class AsyncPipeline:
        def __init__(self):
            self.exists_calls = []

        def exists(self, key):
            self.exists_calls.append(key)
            return self

        async def execute(self):
            return [0]

    class AsyncRedis:
        async def pipeline(self):
            return AsyncPipeline()

    redis = AsyncRedis()
    called = False

    async def fake_connectivity(_redis, currency):
        nonlocal called
        called = True

    monkeypatch.setattr(
        "src.common.redis_protocol.probability_store.verification.run_direct_connectivity_test",
        fake_connectivity,
    )

    with pytest.raises(ProbabilityStoreError, match="Probability storage verification failed"):
        await verify_probability_storage(redis, ["sample-key"], "BTC")
    assert called is True


@pytest.mark.asyncio
async def test_run_direct_connectivity_test_performs_cycle():
    class AsyncRedis:
        def __init__(self):
            self.calls = []

        async def set(self, key, value):
            self.calls.append(("set", key, value))

        async def get(self, key):
            self.calls.append(("get", key))
            return "test_value"

        async def delete(self, key):
            self.calls.append(("delete", key))

    redis = AsyncRedis()
    await run_direct_connectivity_test(redis, "BTC")
    operations = [call[0] for call in redis.calls]
    assert operations == ["set", "get", "delete"]
