from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.common.health.process_health_monitor import (
    ProcessHealthInfo,
    ProcessHealthMonitor,
    ProcessStatus,
)

_TEST_ID_123 = 123
_VAL_12_5 = 12.5


class FakeProcessInfo:
    def __init__(self, pid: int):
        self.pid = pid
        self.last_seen = 123.0


@pytest.mark.asyncio
async def test_get_process_status_not_found(monkeypatch):
    monitor = ProcessHealthMonitor()
    fake_monitor = AsyncMock()
    fake_monitor.get_service_processes = AsyncMock(return_value=[])

    monkeypatch.setattr(
        "src.common.health.process_health_monitor.get_global_process_monitor",
        AsyncMock(return_value=fake_monitor),
    )

    status = await monitor.get_process_status("service")
    assert status.status == ProcessStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_get_process_status_running_without_psutil(monkeypatch):
    monitor = ProcessHealthMonitor()
    fake_monitor = AsyncMock()
    fake_monitor.get_service_processes = AsyncMock(return_value=[FakeProcessInfo(pid=123)])

    monkeypatch.setattr(
        "src.common.health.process_health_monitor.get_global_process_monitor",
        AsyncMock(return_value=fake_monitor),
    )
    monkeypatch.setattr("src.common.health.process_health_monitor.psutil", None)

    status = await monitor.get_process_status("service")
    assert status.status == ProcessStatus.RUNNING
    assert status.pid == _TEST_ID_123


@pytest.mark.asyncio
async def test_get_process_status_uses_psutil(monkeypatch):
    monitor = ProcessHealthMonitor()
    fake_monitor = AsyncMock()
    fake_monitor.get_service_processes = AsyncMock(return_value=[FakeProcessInfo(pid=321)])

    class FakePsutilProcess:
        def __init__(self, pid):
            self._pid = pid

        def is_running(self):
            return True

        def memory_percent(self):
            return 12.5

    fake_psutil = SimpleNamespace(Process=lambda pid: FakePsutilProcess(pid))

    monkeypatch.setattr(
        "src.common.health.process_health_monitor.get_global_process_monitor",
        AsyncMock(return_value=fake_monitor),
    )
    monkeypatch.setattr("src.common.health.process_health_monitor.psutil", fake_psutil)

    status = await monitor.get_process_status("svc")
    assert status.status == ProcessStatus.RUNNING
    assert status.memory_percent == _VAL_12_5


@pytest.mark.asyncio
async def test_get_all_service_process_status(monkeypatch):
    monitor = ProcessHealthMonitor()
    fake_monitor = AsyncMock()
    fake_monitor.get_service_processes = AsyncMock(return_value=[FakeProcessInfo(pid=1)])

    monkeypatch.setattr(
        "src.common.health.process_health_monitor.get_global_process_monitor",
        AsyncMock(return_value=fake_monitor),
    )
    monkeypatch.setattr("src.common.health.process_health_monitor.psutil", None)

    result = await monitor.get_all_service_process_status(["a", "b"])
    assert result["a"].status == ProcessStatus.RUNNING
    assert result["b"].status == ProcessStatus.RUNNING
