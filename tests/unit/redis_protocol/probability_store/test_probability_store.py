"""Tests for ProbabilityStore orchestrator."""

import asyncio

import pytest

from src.common.redis_protocol.probability_store.exceptions import (
    ProbabilityStoreError,
    ProbabilityStoreInitializationError,
)
from src.common.redis_protocol.probability_store.store import ProbabilityStore


class DummyRedis:
    def __init__(self):
        self.data = {}

    async def set(self, key, value):
        self.data[key] = value
        return True

    async def get(self, key):
        return self.data.get(key)


@pytest.mark.asyncio
async def test_probability_store_requires_init():
    store = ProbabilityStore()
    with pytest.raises(ProbabilityStoreInitializationError):
        await store._get_redis()


@pytest.mark.asyncio
async def test_probability_store_uses_injection_and_retrieval(monkeypatch):
    redis = DummyRedis()
    store = ProbabilityStore(redis)

    class FakeIngest:
        async def store_probabilities(self, currency, data):
            await redis.set(currency, data)
            return True

    class FakeRetrieval:
        async def get_probabilities(self, currency):
            return await redis.get(currency)

    monkeypatch.setattr(store, "_ingestion", FakeIngest())
    monkeypatch.setattr(store, "_retrieval", FakeRetrieval())

    result = await store.store_probabilities("btc", {"k": "v"})
    assert result is True
    fetched = await store.get_probabilities("btc")
    assert fetched == {"k": "v"}

    with pytest.raises(ProbabilityStoreError):

        class BrokenIngest:
            async def store_probabilities(self, currency, data):
                raise ProbabilityStoreError("boom")

        monkeypatch.setattr(store, "_ingestion", BrokenIngest())
        await store.store_probabilities("eth", {"k": "v"})
