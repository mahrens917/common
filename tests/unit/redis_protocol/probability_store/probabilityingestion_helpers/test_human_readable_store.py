from __future__ import annotations

from types import SimpleNamespace

import pytest
import redis.exceptions

from common.redis_protocol.probability_store.exceptions import ProbabilityStoreError
from common.redis_protocol.probability_store.probabilityingestion_helpers.human_readable_store import (
    HumanReadableStore,
)


class _FakeCollector:
    def __init__(self, keys=None):
        self.keys = keys or []
        self.deleted: list = []

    async def collect_existing_probability_keys(self, _redis, _prefix):
        return list(self.keys)

    def queue_probability_deletes(self, _pipeline, keys):
        self.deleted.extend(keys)


class _FakeEnqueuer:
    def __init__(self, *, raise_exc: Exception | None = None):
        self.raise_exc = raise_exc
        self.calls = 0

    def enqueue_human_readable_records(self, **kwargs):
        if self.raise_exc:
            raise self.raise_exc
        self.calls += 1
        return SimpleNamespace(field_count=2, sample_keys=["k1", "k2"], event_ticker_counts={"ev": 2})


class _StubRedis:
    def __init__(self):
        self.closed = False

    async def aclose(self):
        self.closed = True


@pytest.mark.asyncio
async def test_store_probabilities_human_readable_success(monkeypatch):
    collector = _FakeCollector(keys=["old1"])
    enqueuer = _FakeEnqueuer()
    redis_client = _StubRedis()

    async def _provider():
        return redis_client

    store = HumanReadableStore(_provider, collector, enqueuer)

    async def _create_pipeline(_redis):
        return ["pipeline"]

    async def _execute(pipeline):
        return ["del", "set1", "set2"]

    monkeypatch.setattr(
        "common.redis_protocol.probability_store.probabilityingestion_helpers.human_readable_store.create_pipeline",
        _create_pipeline,
    )
    monkeypatch.setattr(
        "common.redis_protocol.probability_store.probabilityingestion_helpers.human_readable_store.execute_pipeline",
        _execute,
    )

    recorded = {}

    async def _verify(redis, sample_keys, currency):
        recorded["verify"] = (redis, tuple(sample_keys), currency)

    monkeypatch.setattr(
        "common.redis_protocol.probability_store.probabilityingestion_helpers.human_readable_store.verify_probability_storage",
        _verify,
    )
    monkeypatch.setattr(
        "common.redis_protocol.probability_store.probabilityingestion_helpers.human_readable_store.log_event_ticker_summary",
        lambda currency, count, counts: recorded.setdefault("log", (currency, count, counts)),
    )

    result = await store.store_probabilities_human_readable("eth", {"2024-01-01": {"YES": {"10": 0.5}}})

    assert result is True
    assert collector.deleted == ["old1"]
    assert recorded["verify"][2] == "ETH"
    assert recorded["log"][0] == "ETH"
    assert recorded["log"][1] == 2


@pytest.mark.asyncio
async def test_store_probabilities_human_readable_handles_failures(monkeypatch):
    collector = _FakeCollector()
    enqueuer = _FakeEnqueuer(raise_exc=ValueError("bad payload"))
    redis_client = _StubRedis()

    async def _provider():
        return redis_client

    store = HumanReadableStore(_provider, collector, enqueuer)

    async def _create_pipeline(_redis):
        return []

    async def _execute(_pipeline):
        return []

    monkeypatch.setattr(
        "common.redis_protocol.probability_store.probabilityingestion_helpers.human_readable_store.create_pipeline",
        _create_pipeline,
    )
    monkeypatch.setattr(
        "common.redis_protocol.probability_store.probabilityingestion_helpers.human_readable_store.execute_pipeline",
        _execute,
    )

    failure_context = {}

    def _log_failure(data):
        failure_context["data"] = data

    async def _connectivity(redis, currency):
        failure_context["connectivity"] = (redis, currency)

    monkeypatch.setattr(
        "common.redis_protocol.probability_store.probabilityingestion_helpers.human_readable_store.log_event_ticker_summary",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "common.redis_protocol.probability_store.diagnostics.log_failure_context",
        _log_failure,
    )
    monkeypatch.setattr(
        "common.redis_protocol.probability_store.verification.run_direct_connectivity_test",
        _connectivity,
    )

    with pytest.raises(ProbabilityStoreError):
        await store.store_probabilities_human_readable("btc", {"2025-01-01": {}})

    assert failure_context["data"] == {"2025-01-01": {}}
    assert failure_context["connectivity"][1] == "BTC"
