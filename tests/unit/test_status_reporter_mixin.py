"""Unit tests for StatusReporterMixin."""

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from common.redis_schema.operations import ServiceStatusKey
from common.service_lifecycle.status_reporter_mixin import StatusReporterMixin
from common.service_status import ServiceStatus


class ServiceUnderTest(StatusReporterMixin):
    """Test service class for validating mixin behavior."""

    def __init__(self, service_name: str, redis_client):
        super().__init__(service_name=service_name, redis_client=redis_client)


@pytest.fixture
def mock_redis():
    """Create a mock Redis client with pipeline support."""
    redis = AsyncMock()
    redis.hset = AsyncMock()
    redis.hgetall = AsyncMock()
    # Pipeline delegates hset to redis.hset so call tracking works
    pipe = MagicMock()
    pipe.hset = redis.hset
    pipe.expire = MagicMock()
    pipe.execute = AsyncMock()
    redis.pipeline = MagicMock(return_value=pipe)
    return redis


@pytest.fixture
def test_service(mock_redis):
    """Create a test service instance."""
    return ServiceUnderTest(service_name="test_service", redis_client=mock_redis)


@pytest.mark.asyncio
async def test_initialization(test_service):
    """Test that StatusReporterMixin initializes correctly."""
    assert test_service.service_name == "test_service"
    assert test_service.status_key == "ops:status:TEST_SERVICE"
    assert test_service._pid > 0
    assert test_service._start_time <= time.time()


@pytest.mark.asyncio
async def test_report_status_writes_unified_pattern(test_service, mock_redis):
    """Verify status is written to ops:status:<service>."""
    await test_service.report_status(ServiceStatus.READY)

    # Should write to unified pattern
    assert mock_redis.hset.call_count >= 1

    # Find the call to ops:status:TEST_SERVICE
    calls = [call for call in mock_redis.hset.call_args_list]
    unified_call = None
    for call in calls:
        if call[0][0] == "ops:status:TEST_SERVICE":  # First positional arg is the key
            unified_call = call
            break

    assert unified_call is not None, "Should write to ops:status:TEST_SERVICE"


@pytest.mark.asyncio
async def test_report_status_includes_required_fields(test_service, mock_redis):
    """Verify status includes all required fields."""
    await test_service.report_status(ServiceStatus.READY)

    # Find the unified pattern call
    calls = [call for call in mock_redis.hset.call_args_list]
    unified_call = None
    for call in calls:
        if call[0][0] == "ops:status:TEST_SERVICE":
            unified_call = call
            break

    assert unified_call is not None
    mapping = unified_call[1]["mapping"]

    # Required fields
    assert "status" in mapping
    assert mapping["status"] == "ready"
    assert "timestamp" in mapping
    assert "pid" in mapping
    assert "uptime_seconds" in mapping


@pytest.mark.asyncio
async def test_report_status_includes_additional_fields(test_service, mock_redis):
    """Verify service-specific fields are included."""
    await test_service.report_status(
        ServiceStatus.READY,
        stations_monitored=50,
        opportunities_found=10,
        last_trade_time=1234567890.0,
    )

    # Find the unified pattern call
    calls = [call for call in mock_redis.hset.call_args_list]
    unified_call = None
    for call in calls:
        if call[0][0] == "ops:status:TEST_SERVICE":
            unified_call = call
            break

    assert unified_call is not None
    mapping = unified_call[1]["mapping"]

    # Service-specific fields
    assert "stations_monitored" in mapping
    assert mapping["stations_monitored"] == "50"
    assert "opportunities_found" in mapping
    assert mapping["opportunities_found"] == "10"
    assert "last_trade_time" in mapping
    assert mapping["last_trade_time"] == "1234567890.0"


@pytest.mark.asyncio
async def test_register_startup_sets_initializing(test_service, mock_redis):
    """Verify startup sequence sets INITIALIZING status."""
    await test_service.register_startup()

    # Find the unified pattern call
    calls = [call for call in mock_redis.hset.call_args_list]
    unified_call = None
    for call in calls:
        if call[0][0] == "ops:status:TEST_SERVICE":
            unified_call = call
            break

    assert unified_call is not None
    mapping = unified_call[1]["mapping"]
    assert mapping["status"] == "initializing"


@pytest.mark.asyncio
async def test_register_ready(test_service, mock_redis):
    """Verify register_ready sets READY status."""
    await test_service.register_ready(subscriptions_active=10)

    # Find the unified pattern call
    calls = [call for call in mock_redis.hset.call_args_list]
    unified_call = None
    for call in calls:
        if call[0][0] == "ops:status:TEST_SERVICE":
            unified_call = call
            break

    assert unified_call is not None
    mapping = unified_call[1]["mapping"]
    assert mapping["status"] == "ready"
    assert "subscriptions_active" in mapping
    assert mapping["subscriptions_active"] == "10"


@pytest.mark.asyncio
async def test_register_ready_degraded(test_service, mock_redis):
    """Verify register_ready_degraded sets READY_DEGRADED status."""
    await test_service.register_ready_degraded(reason="Weather API unavailable", cache_age_seconds=300)

    # Find the unified pattern call
    calls = [call for call in mock_redis.hset.call_args_list]
    unified_call = None
    for call in calls:
        if call[0][0] == "ops:status:TEST_SERVICE":
            unified_call = call
            break

    assert unified_call is not None
    mapping = unified_call[1]["mapping"]
    assert mapping["status"] == "ready_degraded"
    assert "degraded_reason" in mapping
    assert mapping["degraded_reason"] == "Weather API unavailable"
    assert "cache_age_seconds" in mapping
    assert mapping["cache_age_seconds"] == "300"


@pytest.mark.asyncio
async def test_register_error(test_service, mock_redis):
    """Verify register_error sets ERROR status."""
    await test_service.register_error(error_message="WebSocket connection lost", retry_attempt=3)

    # Find the unified pattern call
    calls = [call for call in mock_redis.hset.call_args_list]
    unified_call = None
    for call in calls:
        if call[0][0] == "ops:status:TEST_SERVICE":
            unified_call = call
            break

    assert unified_call is not None
    mapping = unified_call[1]["mapping"]
    assert mapping["status"] == "error"
    assert "error" in mapping
    assert mapping["error"] == "WebSocket connection lost"
    assert "retry_attempt" in mapping
    assert mapping["retry_attempt"] == "3"


@pytest.mark.asyncio
async def test_register_failed(test_service, mock_redis):
    """Verify register_failed sets FAILED status."""
    await test_service.register_failed(failure_message="Cannot connect to Redis", total_attempts=10)

    # Find the unified pattern call
    calls = [call for call in mock_redis.hset.call_args_list]
    unified_call = None
    for call in calls:
        if call[0][0] == "ops:status:TEST_SERVICE":
            unified_call = call
            break

    assert unified_call is not None
    mapping = unified_call[1]["mapping"]
    assert mapping["status"] == "failed"
    assert "failure_reason" in mapping
    assert mapping["failure_reason"] == "Cannot connect to Redis"
    assert "total_attempts" in mapping
    assert mapping["total_attempts"] == "10"


@pytest.mark.asyncio
async def test_register_shutdown_sets_stopped(test_service, mock_redis):
    """Verify shutdown sequence sets STOPPED status."""
    await test_service.register_shutdown()

    # Should have two calls: STOPPING and STOPPED
    calls = [call for call in mock_redis.hset.call_args_list]
    unified_calls = [call for call in calls if call[0][0] == "ops:status:TEST_SERVICE"]

    assert len(unified_calls) >= 2

    # Last call should be STOPPED
    final_call = unified_calls[-1]
    mapping = final_call[1]["mapping"]
    assert mapping["status"] == "stopped"


@pytest.mark.asyncio
async def test_register_starting(test_service, mock_redis):
    """Verify register_starting sets STARTING status."""
    await test_service.register_starting(waiting_for="kalshi_service", timeout_seconds=30)

    # Find the unified pattern call
    calls = [call for call in mock_redis.hset.call_args_list]
    unified_call = None
    for call in calls:
        if call[0][0] == "ops:status:TEST_SERVICE":
            unified_call = call
            break

    assert unified_call is not None
    mapping = unified_call[1]["mapping"]
    assert mapping["status"] == "starting"
    assert "waiting_for" in mapping
    assert mapping["waiting_for"] == "kalshi_service"


@pytest.mark.asyncio
async def test_register_restarting(test_service, mock_redis):
    """Verify register_restarting sets RESTARTING status."""
    await test_service.register_restarting(reason="Configuration changed")

    # Find the unified pattern call
    calls = [call for call in mock_redis.hset.call_args_list]
    unified_call = None
    for call in calls:
        if call[0][0] == "ops:status:TEST_SERVICE":
            unified_call = call
            break

    assert unified_call is not None
    mapping = unified_call[1]["mapping"]
    assert mapping["status"] == "restarting"
    assert "restart_reason" in mapping
    assert mapping["restart_reason"] == "Configuration changed"


@pytest.mark.asyncio
async def test_legacy_compatibility_dual_write(test_service, mock_redis):
    """Verify writes to both new and old patterns during migration."""
    await test_service.report_status(ServiceStatus.READY)

    # Should have at least 2 hset calls
    assert mock_redis.hset.call_count >= 2

    calls = [call for call in mock_redis.hset.call_args_list]

    # Find unified pattern call
    unified_call = None
    for call in calls:
        if call[0][0] == "ops:status:TEST_SERVICE":
            unified_call = call
            break

    # Find legacy pattern call
    legacy_call = None
    for call in calls:
        if call[0][0] == "status" and len(call[0]) == 3:  # hset(key, field, value)
            legacy_call = call
            break

    assert unified_call is not None, "Should write to unified pattern"
    assert legacy_call is not None, "Should write to legacy pattern"

    # Legacy call should write service name -> status value
    assert legacy_call[0][1] == "test_service"
    assert legacy_call[0][2] == "ready"


@pytest.mark.asyncio
async def test_uptime_property(test_service):
    """Verify uptime_seconds property works."""
    initial_uptime = test_service.uptime_seconds
    assert initial_uptime >= 0

    # Wait a tiny bit
    time.sleep(0.01)

    later_uptime = test_service.uptime_seconds
    assert later_uptime > initial_uptime


@pytest.mark.asyncio
async def test_service_name_property(test_service):
    """Verify service_name property works."""
    assert test_service.service_name == "test_service"


@pytest.mark.asyncio
async def test_status_key_property(test_service):
    """Verify status_key property works."""
    assert test_service.status_key == "ops:status:TEST_SERVICE"
    assert test_service.status_key == ServiceStatusKey(service="test_service").key()


@pytest.mark.asyncio
async def test_report_status_propagates_redis_errors(test_service, mock_redis):
    """Verify Redis errors are propagated to caller."""
    mock_redis.hset.side_effect = Exception("Redis connection failed")

    with pytest.raises(Exception, match="Redis connection failed"):
        await test_service.report_status(ServiceStatus.READY)


@pytest.mark.asyncio
async def test_multiple_services_different_keys():
    """Verify multiple services use different Redis keys."""
    redis1 = AsyncMock()
    redis1.hset = AsyncMock()
    service1 = ServiceUnderTest(service_name="kalshi", redis_client=redis1)

    redis2 = AsyncMock()
    redis2.hset = AsyncMock()
    service2 = ServiceUnderTest(service_name="tracker", redis_client=redis2)

    await service1.report_status(ServiceStatus.READY)
    await service2.report_status(ServiceStatus.READY)

    # Each should write to their own key
    calls1 = [call for call in redis1.hset.call_args_list]
    calls2 = [call for call in redis2.hset.call_args_list]

    # Find unified calls
    unified1 = [call for call in calls1 if call[0][0] == "ops:status:KALSHI"]
    unified2 = [call for call in calls2 if call[0][0] == "ops:status:TRACKER"]

    assert len(unified1) > 0
    assert len(unified2) > 0


@pytest.mark.asyncio
async def test_timestamp_field_is_current(test_service, mock_redis):
    """Verify timestamp field is close to current time."""
    before = time.time()
    await test_service.report_status(ServiceStatus.READY)
    after = time.time()

    # Find the unified pattern call
    calls = [call for call in mock_redis.hset.call_args_list]
    unified_call = None
    for call in calls:
        if call[0][0] == "ops:status:TEST_SERVICE":
            unified_call = call
            break

    assert unified_call is not None
    mapping = unified_call[1]["mapping"]

    timestamp = float(mapping["timestamp"])
    assert before <= timestamp <= after
