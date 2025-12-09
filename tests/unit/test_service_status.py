import json

import pytest

from src.common.service_status import (
    HealthStatus,
    ServiceStatus,
    create_status_data,
    is_service_failed,
    is_service_operational,
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

    assert is_service_operational("ready")
    assert not is_service_operational("stopped")

    assert is_service_failed("error")
    assert is_service_failed("failed")
    assert not is_service_failed("starting")


@pytest.mark.asyncio
async def test_set_service_status_serializes_and_stores(monkeypatch):
    calls = []

    class FakeRedis:
        async def hset(self, *args, **kwargs):
            calls.append((args, kwargs))

    async def fake_get_redis_connection():
        return FakeRedis()

    monkeypatch.setattr("src.common.service_status.get_redis_connection", fake_get_redis_connection)
    monkeypatch.setattr("time.time", lambda: 123.0)

    await set_service_status(
        "pricing",
        ServiceStatus.READY_DEGRADED,
        error="degraded connectivity",
        metadata={"healthy": False},
        health=HealthStatus.DEGRADED.value,
    )

    assert calls[0][0] == ("status", "pricing", "ready_degraded")

    detail_args = calls[1][0]
    assert detail_args[0] == "status:pricing"

    serialized_payload = calls[1][1]["mapping"]
    assert serialized_payload["status"] == "ready_degraded"
    assert serialized_payload["timestamp"] == "123.0"
    assert json.loads(serialized_payload["metadata"]) == {"healthy": False}
    assert serialized_payload["health"] == "degraded"
    assert serialized_payload["error"] == "degraded connectivity"
