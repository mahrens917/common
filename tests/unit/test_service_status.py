import json

import pytest

from common.service_status import (
    HealthStatus,
    ServiceStatus,
    create_status_data,
    is_service_failed,
    is_service_ready,
    set_service_status,
)


def test_create_status_data_includes_timestamp(monkeypatch):
    monkeypatch.setattr("time.time", lambda: 123.456)

    data = create_status_data(ServiceStatus.READY, markets=42)

    assert data == {"status": "ready", "timestamp": 123.456, "markets": 42}


def test_status_helpers_cover_ready_failed_and_operational():
    assert is_service_ready("ready")
    assert is_service_ready("ready_degraded")
    assert not is_service_ready("stopped")

    assert is_service_failed("error")
    assert is_service_failed("failed")
    assert not is_service_failed("starting")


@pytest.mark.asyncio
async def test_set_service_status_serializes_and_stores(monkeypatch):
    calls = []

    class FakePipeline:
        def hset(self, *args, **kwargs):
            calls.append(("hset", args, kwargs))

        def expire(self, *args, **kwargs):
            calls.append(("expire", args, kwargs))

        async def execute(self):
            pass

    class FakeRedis:
        def pipeline(self):
            return FakePipeline()

    async def fake_get_redis_connection():
        return FakeRedis()

    monkeypatch.setattr("common.service_status.get_redis_connection", fake_get_redis_connection)
    monkeypatch.setattr("time.time", lambda: 123.0)

    await set_service_status(
        "pricing",
        ServiceStatus.READY_DEGRADED,
        error="degraded connectivity",
        metadata={"healthy": False},
        health=HealthStatus.DEGRADED.value,
    )

    # First call: unified key write (ops:status:PRICING)
    assert calls[0][0] == "hset"
    unified_key = calls[0][1][0]
    assert unified_key == "ops:status:PRICING"
    serialized_payload = calls[0][2]["mapping"]
    assert serialized_payload["status"] == "ready_degraded"
    assert serialized_payload["timestamp"] == "123.0"
    assert json.loads(serialized_payload["metadata"]) == {"healthy": False}
    assert serialized_payload["health"] == "degraded"
    assert serialized_payload["error"] == "degraded connectivity"

    # Second call: expire on unified key
    assert calls[1][0] == "expire"

    # Only two calls: unified key hset + expire (legacy status hash removed)
    assert len(calls) == 2
