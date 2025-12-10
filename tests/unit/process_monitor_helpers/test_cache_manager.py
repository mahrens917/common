"""Tests for ProcessCacheManager."""

import time

import psutil

from common.process_monitor import ProcessInfo
from common.process_monitor_helpers.cache_manager import ProcessCacheManager


def test_filter_and_freshness_checks():
    manager = ProcessCacheManager(cache_ttl_seconds=10)
    now = 100.0
    fresh = ProcessInfo(pid=1, name="a", cmdline=[], last_seen=95.0)
    stale = ProcessInfo(pid=2, name="b", cmdline=[], last_seen=80.0)

    filtered = manager.filter_fresh_processes([fresh, stale], current_time=now)

    assert filtered == [fresh]
    assert manager.is_process_fresh(fresh, current_time=now)
    assert not manager.is_process_fresh(stale, current_time=now)


def test_update_process_metrics_removes_dead_process(monkeypatch):
    manager = ProcessCacheManager(cache_ttl_seconds=10)
    cache = {1: ProcessInfo(pid=1, name="a", cmdline=[], last_seen=time.time())}

    def fake_process(_pid):
        raise psutil.NoSuchProcess(1)

    monkeypatch.setattr("common.process_monitor_helpers.cache_manager.psutil.Process", fake_process)

    result = manager.update_process_metrics(1, cache)

    assert result is None
    assert 1 not in cache


def test_update_process_metrics_updates_existing(monkeypatch):
    manager = ProcessCacheManager(cache_ttl_seconds=10)
    cache = {2: ProcessInfo(pid=2, name="b", cmdline=[], last_seen=0.0)}

    class DummyProcess:
        pass

    monkeypatch.setattr(
        "common.process_monitor_helpers.cache_manager.psutil.Process",
        lambda pid: DummyProcess(),
    )

    result = manager.update_process_metrics(2, cache)

    assert result is cache[2]
    assert result.last_seen > 0
