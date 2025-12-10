import json
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from common.connection_state import ConnectionState
from common.redis_protocol.connection_store import ConnectionStateInfo, ConnectionStore


class FakeRedis:
    def __init__(self):
        self.storage = {}
        self.hashes = {}
        self.sorted = {}

    async def hset(self, key, field, value):
        self.hashes.setdefault(key, {})[field] = value

    async def hget(self, key, field):
        return self.hashes.get(key, {}).get(field)

    async def hgetall(self, key):
        return self.hashes.get(key, {}).copy()

    async def hdel(self, key, field):
        self.hashes.get(key, {}).pop(field, None)

    async def expire(self, key, ttl):
        return True

    async def set(self, key, value):
        self.storage[key] = value

    async def get(self, key):
        return self.storage.get(key)

    async def zadd(self, key, mapping):
        self.sorted.setdefault(key, []).extend(mapping.items())

    async def zrangebyscore(self, key, min_score, max_score):
        return [item for item, score in self.sorted.get(key, []) if score >= min_score]

    async def zremrangebyscore(self, key, min_score, max_score):
        entries = self.sorted.get(key, [])
        self.sorted[key] = [item for item in entries if not (min_score <= item[1] <= max_score)]


@pytest.mark.asyncio
async def test_store_and_get_connection_state(monkeypatch):
    fake = FakeRedis()
    store = ConnectionStore()
    monkeypatch.setattr(
        "common.redis_protocol.connection_store.get_redis_pool",
        AsyncMock(return_value=None),
    )
    store.redis_client = fake  # type: ignore[assignment]
    await store._initialization_manager._initialize_helpers()

    state = ConnectionStateInfo(
        service_name="svc",
        state=ConnectionState.CONNECTED,
        timestamp=1.0,
        in_reconnection=False,
    )

    assert await store.store_connection_state(state) is True
    retrieved = await store.get_connection_state("svc")
    assert retrieved is not None
    assert retrieved.state == ConnectionState.CONNECTED


@pytest.mark.asyncio
async def test_store_service_metrics_and_retrieve(monkeypatch):
    fake = FakeRedis()
    store = ConnectionStore()
    store.redis_client = fake  # type: ignore[assignment]
    await store._initialization_manager._initialize_helpers()

    metrics = {"latency": 123}
    assert await store.store_service_metrics("svc", metrics) is True
    retrieved = await store.get_service_metrics("svc")
    assert retrieved == metrics


@pytest.mark.asyncio
async def test_reconnection_events(monkeypatch):
    fake = FakeRedis()
    store = ConnectionStore()
    store.redis_client = fake  # type: ignore[assignment]
    await store._initialization_manager._initialize_helpers()

    await store.record_reconnection_event("svc", "start", "details")
    events = await store.get_recent_reconnection_events("svc", hours_back=1)
    assert len(events) == 1
    assert events[0]["event_type"] == "start"


@pytest.mark.asyncio
async def test_cleanup_stale_states(monkeypatch):
    fake = FakeRedis()
    store = ConnectionStore()
    store.redis_client = fake  # type: ignore[assignment]
    await store._initialization_manager._initialize_helpers()

    old_state = ConnectionStateInfo(
        service_name="old",
        state=ConnectionState.CONNECTED,
        timestamp=0,
        in_reconnection=False,
    )
    new_state = ConnectionStateInfo(
        service_name="new",
        state=ConnectionState.CONNECTED,
        timestamp=time.time(),
        in_reconnection=False,
    )

    await store.store_connection_state(old_state)
    await store.store_connection_state(new_state)

    cleaned = await store.cleanup_stale_states(max_age_hours=1)
    assert cleaned == 1
    assert await store.get_connection_state("old") is None
    assert await store.get_connection_state("new") is not None


@pytest.mark.asyncio
async def test_store_connection_state_handles_errors(caplog):
    class FailingRedis(FakeRedis):
        async def hset(self, key, field, value):
            raise RuntimeError("redis down")

    store = ConnectionStore()
    store.redis_client = FailingRedis()  # type: ignore[assignment]
    await store._initialization_manager._initialize_helpers()

    state = ConnectionStateInfo(
        service_name="svc",
        state=ConnectionState.CONNECTED,
        timestamp=1.0,
        in_reconnection=False,
    )

    with caplog.at_level("ERROR"):
        ok = await store.store_connection_state(state)

    assert ok is False
    assert any("Failed to store connection state" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_get_connection_state_returns_none_for_invalid_enum():
    store = ConnectionStore()
    fake = FakeRedis()
    fake.hashes[store.connection_states_key] = {
        "svc": json.dumps(
            {
                "service_name": "svc",
                "state": "UNKNOWN_STATUS",
                "timestamp": 1.0,
                "in_reconnection": False,
                "consecutive_failures": 0,
            }
        )
    }
    store.redis_client = fake  # type: ignore[assignment]
    await store._initialization_manager._initialize_helpers()

    assert await store.get_connection_state("svc") is None


@pytest.mark.asyncio
async def test_get_all_connection_states_ignores_unparsable_entries():
    store = ConnectionStore()
    fake = FakeRedis()
    fake.hashes[store.connection_states_key] = {
        "good": json.dumps(
            {
                "service_name": "good",
                "state": ConnectionState.CONNECTED.value,
                "timestamp": 3.0,
                "in_reconnection": False,
                "consecutive_failures": 0,
            }
        ),
        "bad": "not-json",
    }
    store.redis_client = fake  # type: ignore[assignment]
    await store._initialization_manager._initialize_helpers()

    states = await store.get_all_connection_states()
    assert list(states.keys()) == ["good"]
    assert states["good"].state == ConnectionState.CONNECTED


@pytest.mark.asyncio
async def test_get_services_in_reconnection_filters_states():
    store = ConnectionStore()
    fake = FakeRedis()
    store.redis_client = fake  # type: ignore[assignment]
    await store._initialization_manager._initialize_helpers()

    await store.store_connection_state(
        ConnectionStateInfo(
            service_name="ready",
            state=ConnectionState.READY,
            timestamp=time.time(),
            in_reconnection=False,
        )
    )
    await store.store_connection_state(
        ConnectionStateInfo(
            service_name="reconnecting",
            state=ConnectionState.RECONNECTING,
            timestamp=time.time(),
            in_reconnection=True,
        )
    )
    await store.store_connection_state(
        ConnectionStateInfo(
            service_name="connecting",
            state=ConnectionState.CONNECTING,
            timestamp=time.time(),
            in_reconnection=False,
        )
    )

    services = await store.get_services_in_reconnection()
    assert set(services) == {"reconnecting", "connecting"}


@pytest.mark.asyncio
async def test_get_recent_reconnection_events_handles_parse_errors(caplog):
    store = ConnectionStore()
    fake = FakeRedis()
    fake.sorted[store.reconnection_events_key] = [
        ("not-json", time.time()),
        (
            json.dumps(
                {
                    "service_name": "svc",
                    "event_type": "start",
                    "timestamp": time.time(),
                    "details": "ok",
                }
            ),
            time.time(),
        ),
    ]
    store.redis_client = fake  # type: ignore[assignment]
    await store._initialization_manager._initialize_helpers()

    with caplog.at_level("WARNING"):
        events = await store.get_recent_reconnection_events("svc", hours_back=1)

    assert len(events) == 1
    assert events[0]["event_type"] == "start"
    assert any("Failed to parse reconnection event" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_get_recent_reconnection_events_returns_empty_on_error(caplog):
    class FailingRedis(FakeRedis):
        async def zrangebyscore(self, key, min_score, max_score):
            raise RuntimeError("fail")

    store = ConnectionStore()
    store.redis_client = FailingRedis()  # type: ignore[assignment]
    await store._initialization_manager._initialize_helpers()

    with caplog.at_level("ERROR"):
        events = await store.get_recent_reconnection_events("svc", hours_back=1)

    assert events == []
    assert any("Failed to get reconnection events" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_get_service_metrics_returns_none_on_error(caplog):
    class FailingRedis(FakeRedis):
        async def get(self, key):
            raise RuntimeError("oops")

    store = ConnectionStore()
    store.redis_client = FailingRedis()  # type: ignore[assignment]
    await store._initialization_manager._initialize_helpers()

    with caplog.at_level("ERROR"):
        metrics = await store.get_service_metrics("svc")

    assert metrics is None
    assert any("Failed to get connection metrics" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_store_service_metrics_returns_false_on_error(caplog):
    class FailingRedis(FakeRedis):
        async def set(self, key, value):
            raise RuntimeError("set failed")

    store = ConnectionStore()
    store.redis_client = FailingRedis()  # type: ignore[assignment]
    await store._initialization_manager._initialize_helpers()

    with caplog.at_level("ERROR"):
        ok = await store.store_service_metrics("svc", {"latency": 1})

    assert ok is False
    assert any("Failed to store connection metrics" in record.message for record in caplog.records)
