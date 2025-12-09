import asyncio
from unittest.mock import Mock

import pytest

from src.common.health.types import BaseHealthMonitor, HealthCheckResult


class DummyHealthMonitor(BaseHealthMonitor):
    async def check_health(self) -> HealthCheckResult:
        return HealthCheckResult(healthy=True)


def test_record_success_with_timestamp(monkeypatch):
    monitor = DummyHealthMonitor("dummy")
    fake_loop = Mock()
    fake_loop.time.return_value = 1.0
    monkeypatch.setattr(asyncio, "get_running_loop", Mock(return_value=fake_loop))
    monitor.record_success(timestamp=1.23)
    assert monitor.last_success_time == 1.23
    assert monitor.consecutive_failures == 0


def test_record_success_uses_loop_time(monkeypatch):
    monitor = DummyHealthMonitor("dummy")
    fake_loop = Mock()
    fake_loop.time.return_value = 3.14
    monkeypatch.setattr(asyncio, "get_running_loop", Mock(return_value=fake_loop))

    monitor.record_success()
    assert monitor.last_success_time == 3.14


def test_record_failure_increments():
    monitor = DummyHealthMonitor("dummy")
    monitor.record_failure()
    assert monitor.consecutive_failures == 1


def test_reset_counters_zeroes_state():
    monitor = DummyHealthMonitor("dummy")
    monitor.consecutive_failures = 5
    monitor.last_success_time = 10.0

    monitor.reset_counters()
    assert monitor.consecutive_failures == 0
    assert monitor.last_success_time == 0.0


def test_alias_methods():
    monitor = DummyHealthMonitor("dummy")
    monitor.consecutive_failures = 2
    monitor.last_success_time = 7.5

    monitor.increment_failures()
    assert monitor.consecutive_failures == 3

    monitor.reset_failures()
    assert monitor.consecutive_failures == 0
    assert monitor.last_success_time == 0.0


def test_should_raise_error():
    monitor = DummyHealthMonitor("dummy")
    monitor.consecutive_failures = 3
    assert monitor.should_raise_error(3) is True
    assert monitor.should_raise_error(4) is False
