import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from common.health.health_aggregator import ServiceHealthAggregator
from common.health.health_types import OverallServiceStatus

_VAL_42_5 = 42.5

from common.health.log_activity_monitor import LogActivity, LogActivityStatus
from common.health.process_health_monitor import ProcessHealthInfo, ProcessStatus
from common.health.service_health_types import ServiceHealth, ServiceHealthInfo


def make_aggregator(monkeypatch, *, process_result, log_result, service_result):
    aggregator = ServiceHealthAggregator()
    monkeypatch.setattr(aggregator.process_monitor, "get_process_status", AsyncMock(return_value=process_result))
    monkeypatch.setattr(aggregator.log_monitor, "get_log_activity", AsyncMock(return_value=log_result))
    monkeypatch.setattr(aggregator.health_checker, "check_service_health", AsyncMock(return_value=service_result))
    return aggregator


@pytest.mark.asyncio
async def test_get_service_status_aggregates_healthy(monkeypatch):
    aggregator = make_aggregator(
        monkeypatch,
        process_result=ProcessHealthInfo(status=ProcessStatus.RUNNING, memory_percent=42.5),
        log_result=LogActivity(status=LogActivityStatus.RECENT, age_seconds=30),
        service_result=ServiceHealthInfo(health=ServiceHealth.HEALTHY),
    )

    result = await aggregator.get_service_status("weather")

    assert result.overall_status is OverallServiceStatus.HEALTHY
    assert result.status_message == "Healthy"
    assert result.memory_percent == _VAL_42_5
    assert "logs: 30s ago" in result.detailed_message


@pytest.mark.asyncio
async def test_get_service_status_handles_log_error(monkeypatch):
    aggregator = make_aggregator(
        monkeypatch,
        process_result=ProcessHealthInfo(status=ProcessStatus.RUNNING),
        log_result=LogActivity(status=LogActivityStatus.ERROR, error_message="missing"),
        service_result=ServiceHealthInfo(health=ServiceHealth.HEALTHY),
    )

    result = await aggregator.get_service_status("weather")

    assert result.overall_status is OverallServiceStatus.SILENT
    assert "Silent" in result.status_message
    assert "error" in result.detailed_message


@pytest.mark.asyncio
async def test_get_service_status_process_not_found(monkeypatch):
    aggregator = make_aggregator(
        monkeypatch,
        process_result=ProcessHealthInfo(status=ProcessStatus.NOT_FOUND),
        log_result=LogActivity(status=LogActivityStatus.RECENT, age_seconds=60),
        service_result=ServiceHealthInfo(health=ServiceHealth.UNKNOWN),
    )

    result = await aggregator.get_service_status("worker")

    assert result.overall_status is OverallServiceStatus.NOT_FOUND
    assert "process: not found" in result.detailed_message


@pytest.mark.asyncio
async def test_get_all_service_status_returns_error_on_exception(monkeypatch):
    aggregator = ServiceHealthAggregator()

    ok_status = MagicMock()
    ok_status.service_name = "svc-b"
    ok_status.overall_status = OverallServiceStatus.HEALTHY
    ok_status.process_info = ProcessHealthInfo(status=ProcessStatus.RUNNING)
    ok_status.log_activity = LogActivity(status=LogActivityStatus.RECENT, age_seconds=0)
    ok_status.service_health = ServiceHealthInfo(health=ServiceHealth.HEALTHY)
    ok_status.status_emoji = "🟢"
    ok_status.status_message = "Healthy"
    ok_status.detailed_message = "ok"
    ok_status.memory_percent = None
    ok_status.log_age_seconds = None
    monkeypatch.setattr(
        aggregator.multi_checker,
        "get_single_service_status",
        AsyncMock(side_effect=[RuntimeError("boom"), ok_status]),
    )

    results = await aggregator.get_all_service_status(["svc-a", "svc-b"])

    assert results["svc-a"].overall_status is OverallServiceStatus.ERROR
    assert "Failed to check status" in results["svc-a"].detailed_message


def test_format_status_line_includes_memory(monkeypatch):
    aggregator = ServiceHealthAggregator()
    result = SimpleNamespace(
        status_emoji="🟢",
        service_name="weather",
        status_message="Healthy",
        detailed_message="process: running",
        memory_percent=55.123,
    )

    line = aggregator.format_status_line(result)

    assert "weather" in line
    assert "55.1%" in line
