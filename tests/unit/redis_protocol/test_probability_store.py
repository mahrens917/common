from __future__ import annotations

import math
from decimal import Decimal

import pytest

from src.common.redis_protocol.probability_store import (
    ProbabilityData,
    ProbabilityDataNotFoundError,
    ProbabilityStore,
    ProbabilityStoreError,
)

_VAL_0_73 = 0.73


@pytest.fixture
def probability_store(fake_redis):
    return ProbabilityStore(redis=fake_redis)


@pytest.mark.asyncio
async def test_store_and_get_probabilities_roundtrip(probability_store: ProbabilityStore):
    payload = {
        "2025-01-01T00:00:00Z": {
            "1000": {
                "probability": Decimal("0.55"),
                "error": Decimal("0.0125"),
                "confidence": 0.95,
            },
            "2000": {"probability": 0.25, "error": 0.08},
        },
        "2025-01-02T00:00:00Z": {
            "2500": {"probability": 0.45, "confidence": Decimal("0.99")},
        },
    }

    await probability_store.store_probabilities("btc", payload)
    stored = await probability_store.get_probabilities("btc")

    assert stored == {
        "2025-01-01T00:00:00Z": {
            "1000": {"probability": 0.55, "error": 0.0125, "confidence": 0.95},
            "2000": {"probability": 0.25, "error": 0.08},
        },
        "2025-01-02T00:00:00Z": {
            "2500": {"probability": 0.45, "confidence": 0.99},
        },
    }


@pytest.mark.asyncio
async def test_store_probabilities_empty_payload(probability_store: ProbabilityStore, fake_redis):
    await probability_store.store_probabilities("eth", {})

    redis_key = "probabilities:ETH"
    assert fake_redis.dump_hash(redis_key) == {}

    with pytest.raises(ProbabilityDataNotFoundError):
        await probability_store.get_probabilities("eth")


@pytest.mark.asyncio
async def test_store_probabilities_large_snapshot(probability_store: ProbabilityStore, fake_redis):
    payload = {}
    total_strikes = 0

    for day in range(1, 6):
        expiry = f"2025-01-{day:02d}T00:00:00Z"
        strikes = {}
        for offset in range(50):
            strike = str(10000 + offset)
            strikes[strike] = {"probability": (offset + day) / 100.0, "confidence": 0.8}
            total_strikes += 1
        payload[expiry] = strikes

    await probability_store.store_probabilities("usd", payload)

    redis_key = "probabilities:USD"
    assert len(fake_redis.dump_hash(redis_key)) == total_strikes

    roundtrip = await probability_store.get_probabilities("USD")
    sample_expiry = "2025-01-03T00:00:00Z"
    assert roundtrip[sample_expiry]["10005"]["probability"] == pytest.approx(0.08)


@pytest.mark.asyncio
async def test_store_probability_partial_update(probability_store: ProbabilityStore, fake_redis):
    data = ProbabilityData(
        currency="eur",
        expiry="2025-02-01T00:00:00Z",
        strike_type="greater",
        strike=12345.5,
        probability=Decimal("0.73"),
        error=None,
        confidence=math.nan,
        probability_range=(Decimal("0.50"), None),
    )
    await probability_store.store_probability(data)

    redis_key = "probabilities:EUR:2025-02-01T00:00:00Z:greater:12346"
    stored = fake_redis.dump_hash(redis_key)
    assert stored == {
        "probability": "0.73",
        "confidence": "NaN",
        "range_low": "0.5",
        "range_high": "null",
    }

    fetched = await probability_store.get_probability_data(
        "eur", "2025-02-01T00:00:00Z", "12346", "greater"
    )
    assert fetched["probability"] == _VAL_0_73
    assert fetched["confidence"] == "NaN"
    assert fetched["range_high"] == "null"


@pytest.mark.asyncio
async def test_store_probabilities_human_readable_rounds_and_preserves_nan(
    probability_store: ProbabilityStore, fake_redis, stub_schema_config
):
    payload = {
        "2025-03-01T00:00:00Z": {
            "12345.6": {
                "strike_type": "greater",
                "probability": 0.42,
                "error": math.nan,
                "confidence": 0.75,
                "range_low": 0.1,
                "range_high": None,
                "event_ticker": "BTC-FOO",
            }
        }
    }

    stored = await probability_store.store_probabilities_human_readable("btc", payload)
    assert stored is True

    redis_key = "probabilities:BTC:2025-03-01T00:00:00Z:greater:12346"
    assert fake_redis.dump_hash(redis_key) == {
        "probability": "0.42",
        "error": "nan",
        "confidence": "0.75",
        "range_low": "0.1",
        "range_high": "null",
        "event_ticker": "BTC-FOO",
    }


@pytest.mark.asyncio
async def test_get_probabilities_human_readable_requires_data(probability_store):
    with pytest.raises(ProbabilityDataNotFoundError):
        await probability_store.get_probabilities_human_readable("btc")


@pytest.mark.asyncio
async def test_get_probabilities_human_readable_requires_event_title(
    probability_store: ProbabilityStore, fake_redis
):
    await fake_redis.hset(
        "probabilities:BTC:2025-04-01T00:00:00Z:call:100",
        mapping={
            "probability": "0.6",
            "event_title": "Spring Storms",
        },
    )
    await fake_redis.hset(
        "probabilities:BTC:2025-04-01T00:00:00Z:put:200",
        mapping={
            "probability": "0.4",
        },
    )

    with pytest.raises(ProbabilityStoreError, match="Missing event_title"):
        await probability_store.get_probabilities_human_readable("btc")


@pytest.mark.asyncio
async def test_get_probabilities_human_readable_groups_when_titles_present(
    probability_store: ProbabilityStore, fake_redis
):
    await fake_redis.hset(
        "probabilities:BTC:2025-04-01T00:00:00Z:call:100",
        mapping={
            "probability": "0.6",
            "confidence": "NaN",
            "event_title": "Spring Storms",
            "event_type": "weather",
        },
    )
    await fake_redis.hset(
        "probabilities:BTC:2025-04-01T00:00:00Z:put:200",
        mapping={
            "probability": "0.4",
            "event_title": "Spring Storms",
        },
    )

    result = await probability_store.get_probabilities_human_readable("btc")

    bucket = result["2025-04-01T00:00:00Z"]["Spring Storms"]
    assert bucket["call"]["100"]["probability"] == pytest.approx(0.6)
    assert bucket["call"]["100"]["confidence"] == "NaN"
    assert bucket["put"]["200"]["probability"] == pytest.approx(0.4)


@pytest.mark.asyncio
async def test_get_all_event_types_ignores_nulls(probability_store: ProbabilityStore, fake_redis):
    await fake_redis.hset(
        "probabilities:BTC:2025-05-01:call:100",
        mapping={"event_type": "rain"},
    )
    await fake_redis.hset(
        "probabilities:BTC:2025-05-02:call:101",
        mapping={"event_type": "null"},
    )
    await fake_redis.hset(
        "probabilities:BTC:2025-05-03:call:102",
        mapping={"event_type": "snow"},
    )

    event_types = await probability_store.get_all_event_types("btc")
    assert event_types == ["rain", "snow"]


@pytest.mark.asyncio
async def test_get_probabilities_by_event_type_filters_and_sorts(
    probability_store: ProbabilityStore, fake_redis
):
    await fake_redis.hset(
        "probabilities:BTC:2025-06-02T00:00:00Z:call:120",
        mapping={"probability": "0.7", "event_type": "rain"},
    )
    await fake_redis.hset(
        "probabilities:BTC:2025-06-01T00:00:00Z:call:110",
        mapping={"probability": "0.5", "event_type": "rain"},
    )
    await fake_redis.hset(
        "probabilities:BTC:2025-06-03T00:00:00Z:call:130",
        mapping={"probability": "0.3", "event_type": "snow"},
    )

    result = await probability_store.get_probabilities_by_event_type("btc", "rain")

    assert list(result.keys()) == [
        "2025-06-01T00:00:00Z",
        "2025-06-02T00:00:00Z",
    ]
    first_expiry = result["2025-06-01T00:00:00Z"]
    assert first_expiry["call"]["110"]["probability"] == pytest.approx(0.5)
    second_expiry = result["2025-06-02T00:00:00Z"]
    assert second_expiry["call"]["120"]["probability"] == pytest.approx(0.7)
