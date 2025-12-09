from __future__ import annotations

import asyncio
import time
from typing import Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.common.health.service_health_checker import (
    ServiceHealth,
    ServiceHealthChecker,
    ServiceHealthInfo,
)

_CENTS_1700000000 = 1_700_000_000


@pytest.mark.asyncio
async def test_check_service_health_uses_redis_status(monkeypatch):
    import time

    checker = ServiceHealthChecker()
    current_time = time.time()
    mock_info = ServiceHealthInfo(ServiceHealth.HEALTHY, last_status_update=current_time)
    monkeypatch.setattr(
        "src.common.health.service_health_checker_helpers.redis_status_checker.check_redis_status",
        AsyncMock(return_value=mock_info),
    )

    result = await checker.check_service_health("deribit")
    assert result == mock_info


@pytest.mark.asyncio
async def test_check_service_health_handles_exception(monkeypatch):
    checker = ServiceHealthChecker()
    monkeypatch.setattr(
        "src.common.health.service_health_checker_helpers.redis_status_checker.check_redis_status",
        AsyncMock(side_effect=RuntimeError("boom")),
    )

    result = await checker.check_service_health("kalshi")
    # When Redis check fails, it falls back to status staleness check
    assert result.health in (ServiceHealth.DEGRADED, ServiceHealth.UNKNOWN)
    assert result.error_message is not None


def make_status_data(status: str, timestamp: float) -> Dict[str, bytes]:
    return {"status".encode(): status.encode(), "timestamp".encode(): str(timestamp).encode()}


@pytest.mark.asyncio
async def test_check_redis_status_reports_healthy(monkeypatch):
    checker = ServiceHealthChecker()
    redis = MagicMock()
    redis.hgetall = AsyncMock(return_value=make_status_data("operational", 1_700_000_000))
    monkeypatch.setattr(time, "time", lambda: 1_700_000_100)
    monkeypatch.setattr(
        "src.common.redis_protocol.converters.decode_redis_hash",
        lambda data: {k.decode(): v.decode() for k, v in data.items()},
    )
    monkeypatch.setattr(
        "src.common.redis_protocol.typing.ensure_awaitable",
        lambda coro: coro,
    )
    monkeypatch.setattr(checker, "_get_redis_client", AsyncMock(return_value=redis))
    from src.common import service_status

    monkeypatch.setattr(service_status, "is_service_failed", lambda status: status == "failed")
    monkeypatch.setattr(
        service_status, "is_service_operational", lambda status: status == "operational"
    )

    from src.common.health.service_health_checker_helpers.redis_status_checker import (
        check_redis_status,
    )

    info = await check_redis_status("deribit", redis)

    assert info.health == ServiceHealth.HEALTHY
    assert info.last_status_update == _CENTS_1700000000


@pytest.mark.asyncio
async def test_check_redis_status_handles_stale_operational_status(monkeypatch):
    checker = ServiceHealthChecker()
    redis = MagicMock()
    redis.hgetall = AsyncMock(return_value=make_status_data("operational", 1_700_000_000))
    monkeypatch.setattr(checker, "_get_redis_client", AsyncMock(return_value=redis))
    monkeypatch.setattr(time, "time", lambda: 1_700_001_000)
    monkeypatch.setattr(
        "src.common.redis_protocol.converters.decode_redis_hash",
        lambda data: {k.decode(): v.decode() for k, v in data.items()},
    )
    monkeypatch.setattr(
        "src.common.redis_protocol.typing.ensure_awaitable",
        lambda coro: coro,
    )
    from src.common import service_status

    monkeypatch.setattr(service_status, "is_service_failed", lambda status: False)
    monkeypatch.setattr(
        service_status, "is_service_operational", lambda status: status == "operational"
    )

    from src.common.health.service_health_checker_helpers.redis_status_checker import (
        check_redis_status,
    )

    info = await check_redis_status("deribit", redis)
    assert info.health == ServiceHealth.DEGRADED
    assert "Status stale" in (info.error_message or "")


@pytest.mark.asyncio
async def test_check_redis_status_handles_failed_status(monkeypatch):
    checker = ServiceHealthChecker()
    redis = MagicMock()
    redis.hgetall = AsyncMock(return_value=make_status_data("failed", 1_700_000_000))
    monkeypatch.setattr(checker, "_get_redis_client", AsyncMock(return_value=redis))
    monkeypatch.setattr(
        "src.common.redis_protocol.converters.decode_redis_hash",
        lambda data: {k.decode(): v.decode() for k, v in data.items()},
    )
    monkeypatch.setattr(
        "src.common.redis_protocol.typing.ensure_awaitable",
        lambda coro: coro,
    )
    from src.common import service_status

    monkeypatch.setattr(service_status, "is_service_failed", lambda status: status == "failed")
    monkeypatch.setattr(service_status, "is_service_operational", lambda status: False)

    from src.common.health.service_health_checker_helpers.redis_status_checker import (
        check_redis_status,
    )

    info = await check_redis_status("deribit", redis)
    assert info.health == ServiceHealth.UNRESPONSIVE
    assert "Service status: failed" in (info.error_message or "")


@pytest.mark.asyncio
async def test_check_redis_status_handles_missing_data(monkeypatch):
    checker = ServiceHealthChecker()
    redis = MagicMock()
    redis.hgetall = AsyncMock(return_value={})
    monkeypatch.setattr(checker, "_get_redis_client", AsyncMock(return_value=redis))
    monkeypatch.setattr(
        "src.common.health.service_health_checker.ensure_awaitable", lambda coro: coro
    )

    from src.common.health.service_health_checker_helpers.redis_status_checker import (
        check_redis_status,
    )

    info = await check_redis_status("deribit", redis)
    assert info.health == ServiceHealth.UNRESPONSIVE
    assert "No status data" in (info.error_message or "")


@pytest.mark.asyncio
async def test_check_redis_status_handles_invalid_timestamp(monkeypatch):
    checker = ServiceHealthChecker()
    redis = MagicMock()
    redis.hgetall = AsyncMock(
        return_value={"status".encode(): b"operational", "timestamp".encode(): b"not-a-number"}
    )
    monkeypatch.setattr(checker, "_get_redis_client", AsyncMock(return_value=redis))
    monkeypatch.setattr(
        "src.common.redis_protocol.converters.decode_redis_hash",
        lambda data: {k.decode(): v.decode() for k, v in data.items()},
    )
    monkeypatch.setattr(
        "src.common.redis_protocol.typing.ensure_awaitable",
        lambda coro: coro,
    )
    from src.common import service_status

    monkeypatch.setattr(service_status, "is_service_failed", lambda status: False)
    monkeypatch.setattr(service_status, "is_service_operational", lambda status: True)

    from src.common.health.service_health_checker_helpers.redis_status_checker import (
        check_redis_status,
    )

    info = await check_redis_status("deribit", redis)
    assert info.health == ServiceHealth.UNRESPONSIVE
    assert "Invalid timestamp" in (info.error_message or "")


@pytest.mark.asyncio
async def test_check_all_service_health_handles_exceptions(monkeypatch):
    checker = ServiceHealthChecker()

    async def mock_check(name):
        if name == "good":
            return ServiceHealthInfo(ServiceHealth.HEALTHY)
        raise RuntimeError("failure")

    monkeypatch.setattr(checker, "check_service_health", AsyncMock(side_effect=mock_check))

    results = await checker.check_all_service_health(["good", "bad"])
    assert results["good"].health == ServiceHealth.HEALTHY
    assert results["bad"].health == ServiceHealth.UNKNOWN
    assert "failure" in (results["bad"].error_message or "")


@pytest.mark.asyncio
async def test_ping_service_returns_true_for_degraded(monkeypatch):
    checker = ServiceHealthChecker()
    monkeypatch.setattr(
        checker,
        "check_service_health",
        AsyncMock(return_value=ServiceHealthInfo(ServiceHealth.DEGRADED)),
    )
    assert await checker.ping_service("kalshi") is True


@pytest.mark.asyncio
async def test_ping_service_returns_false_on_error(monkeypatch):
    checker = ServiceHealthChecker()
    monkeypatch.setattr(
        checker,
        "check_service_health",
        AsyncMock(side_effect=RuntimeError("boom")),
    )
    assert await checker.ping_service("kalshi") is False
