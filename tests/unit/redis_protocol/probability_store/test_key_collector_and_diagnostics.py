from collections import Counter
from types import SimpleNamespace

import pytest

from common.redis_protocol.probability_store.diagnostics import (
    log_event_ticker_summary,
    log_event_type_summary,
    log_failure_context,
    log_human_readable_summary,
    log_probability_diagnostics,
)
from common.redis_protocol.probability_store.probabilityingestion_helpers.key_collector import (
    KeyCollector,
)


class _FakeRedis:
    def __init__(self, keys):
        self.keys_called = []
        self._keys = keys

    async def keys(self, pattern):
        self.keys_called.append(pattern)
        return list(self._keys)


class _FakePipeline:
    def __init__(self):
        self.deleted = []

    def delete(self, key):
        self.deleted.append(key)


@pytest.mark.asyncio
async def test_key_collector_collect_and_delete():
    redis = _FakeRedis(keys=[b"a", "b"])
    collector = KeyCollector()
    keys = await collector.collect_existing_probability_keys(redis, "prefix:")
    assert keys == ["a", "b"]
    assert redis.keys_called == ["prefix:*"]

    pipeline = _FakePipeline()
    collector.queue_probability_deletes(pipeline, keys)
    assert pipeline.deleted == ["a", "b"]


def test_diagnostics_logging(caplog):
    record = SimpleNamespace(
        key="k1",
        diagnostics=SimpleNamespace(
            error_value=None,
            stored_error=None,
            confidence_value=0.2,
            stored_confidence=0.3,
        ),
    )
    with caplog.at_level("DEBUG"):
        log_probability_diagnostics(record)
    assert "No error value provided" in caplog.text
    assert "Confidence value for key k1" in caplog.text

    result = {"exp": {"ev": {"call": {"strike": 10.0}}}}
    with caplog.at_level("DEBUG"):
        log_human_readable_summary("usd", 5, result)
    assert "Processed 5 keys into 1 expiries" in caplog.text

    with caplog.at_level("INFO"):
        log_event_type_summary("usd", "type", 3, result)
        log_event_ticker_summary("usd", 2, Counter({"ev1": 1, "ev2": 1}))
    assert "Retrieved 3 probability keys" in caplog.text
    assert "Event ticker 'ev1'" in caplog.text

    with caplog.at_level("ERROR"):
        log_failure_context({})
        log_failure_context({"exp1": {"strike": {}}})
    assert "probabilities_data contains 0 expiries" in caplog.text
