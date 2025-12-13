from __future__ import annotations

import asyncio
import time

import pytest

from common.process_monitor import ProcessInfo
from common.process_monitor_helpers.scan_coordinator import ScanCoordinator


class _FakeScanner:
    def __init__(self) -> None:
        now = time.time()
        self._proc = ProcessInfo(pid=1, name="python", cmdline=["python"], last_seen=now)

    def perform_full_scan(self):
        return {1: self._proc}, {"svc": [self._proc]}, [self._proc]

    def perform_incremental_scan(self, process_cache):
        _ = process_cache
        return []


@pytest.mark.asyncio
async def test_perform_full_scan_returns_results():
    coordinator = ScanCoordinator(_FakeScanner())

    process_cache, service_cache, redis_processes, timestamp = await coordinator.perform_full_scan({}, {}, [])

    assert 1 in process_cache
    assert "svc" in service_cache
    assert redis_processes
    assert isinstance(timestamp, float)


@pytest.mark.asyncio
async def test_perform_full_scan_returns_empty_on_timeout(monkeypatch):
    coordinator = ScanCoordinator(_FakeScanner())

    async def _raise_timeout(future, *, timeout):
        _ = timeout
        future.cancel()
        raise asyncio.TimeoutError()

    monkeypatch.setattr("common.process_monitor_helpers.scan_coordinator.asyncio.wait_for", _raise_timeout)

    process_cache, service_cache, redis_processes, _timestamp = await coordinator.perform_full_scan({}, {}, [])

    assert process_cache == {}
    assert service_cache == {}
    assert redis_processes == []
