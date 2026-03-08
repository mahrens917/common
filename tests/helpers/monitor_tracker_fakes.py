"""
Test doubles for monitor and tracker dependencies.

These helpers provide deterministic, dependency-free replacements for the
objects created inside `src.monitor.simple_monitor.SimpleMonitor`.  They keep
state so tests can assert behaviour without touching Redis, subprocesses, or
network resources.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional

from common.monitoring import ProcessInfo, ProcessStatus


@dataclass
class FakeAlert:
    message: str
    severity: Optional[str]
    alert_type: Optional[str]


class FakeAlerter:
    """Records alerts and command registrations for verification."""

    def __init__(self) -> None:
        self.command_handlers: Dict[str, Callable[..., Awaitable[Any]]] = {}
        self.alerts: List[FakeAlert] = []
        self.poll_calls = 0
        self.cleaned_up = False

    def register_command_handler(self, command: str, handler: Callable[..., Awaitable[Any]]) -> None:
        self.command_handlers[command] = handler

    async def send_alert(self, message: str, severity: Optional[str] = None, alert_type: Optional[str] = None) -> None:
        self.alerts.append(FakeAlert(message=message, severity=severity, alert_type=alert_type))

    async def poll_telegram_updates(self) -> None:
        self.poll_calls += 1

    async def cleanup(self) -> None:
        self.cleaned_up = True


@dataclass
class FakeHealthCheck:
    """Simple struct mirroring monitor.health_checker.HealthCheck."""

    name: str
    status: Any  # Typically the HealthStatus enum from monitor.health_checker
    message: str = ""


class FakeHealthChecker:
    """Keeps pre-baked health check results and exposes a Redis handle slot."""

    def __init__(
        self,
        *,
        redis_client: Any = None,
        results: Optional[Iterable[FakeHealthCheck]] = None,
    ) -> None:
        self.redis_client = redis_client
        self._results: List[FakeHealthCheck] = list(results or [])
        self.initialized = False
        self.check_calls = 0

    async def initialize(self) -> None:
        self.initialized = True

    async def check_all_health(self) -> List[FakeHealthCheck]:
        self.check_calls += 1
        return list(self._results)

    def set_results(self, results: Iterable[FakeHealthCheck]) -> None:
        self._results = list(results)


class FakeTrackerController:
    """Minimal tracker controller stub used by the monitor tests."""

    def __init__(self, *, enabled: bool = True) -> None:
        self.tracker_enabled = enabled
        self.initialize_calls = 0
        self.status_response: Dict[str, Any] = {
            "enabled": enabled,
            "running": False,
            "pid": None,
            "status_summary": "idle",
        }

    async def initialize(self) -> None:
        self.initialize_calls += 1

    async def get_tracker_status(self) -> Dict[str, Any]:
        return dict(self.status_response)


class FakeProcessManager:
    """Replaces ProcessManager with deterministic async methods."""

    def __init__(
        self,
        *,
        services: Optional[Dict[str, str]] = None,
        start_success: bool = True,
        stop_results: Optional[Dict[str, bool]] = None,
        restart_success: bool | Dict[str, bool] = True,
    ) -> None:
        services = services or {"market_collector": "src.collector"}
        self.services = dict(services)
        self.process_info: Dict[str, ProcessInfo] = {
            name: ProcessInfo(name=name, module_path=module, status=ProcessStatus.STOPPED) for name, module in self.services.items()
        }
        self._start_success = start_success
        self._stop_results = stop_results or {name: True for name in self.services}
        if isinstance(restart_success, dict):
            self._restart_results = restart_success
        else:
            self._restart_results = {name: restart_success for name in self.services}
        self.start_calls = 0
        self.stop_calls = 0
        self.restart_calls: List[str] = []

    async def start_services_with_dependencies(self) -> bool:
        self.start_calls += 1
        for info in self.process_info.values():
            info.status = ProcessStatus.RUNNING if self._start_success else ProcessStatus.FAILED
        return self._start_success

    async def stop_services_in_reverse_dependency_order(self) -> Dict[str, bool]:
        self.stop_calls += 1
        for name in self.process_info:
            self.process_info[name].status = ProcessStatus.STOPPED
        return dict(self._stop_results)

    async def restart_service(self, service_name: str) -> bool:
        self.restart_calls.append(service_name)
        if service_name in self._restart_results:
            success = self._restart_results[service_name]
        else:
            success = True
        self.process_info[service_name].status = ProcessStatus.RUNNING if success else ProcessStatus.FAILED
        return success


class FakeProcessMonitor:
    """Async stub mirroring the global process monitor lifecycle hooks."""

    def __init__(self) -> None:
        self.start_calls = 0
        self.stop_calls = 0

    async def start_background_scanning(self) -> None:
        self.start_calls += 1

    async def stop_background_scanning(self) -> None:
        self.stop_calls += 1


class FakeHistoryMetricsRecorder:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False

    async def start_recording(self) -> None:
        self.started = True

    async def stop_recording(self) -> None:
        self.stopped = True


class FakePriceHistoryTracker:
    def __init__(self) -> None:
        self.initialized = False

    async def initialize(self) -> None:
        self.initialized = True


class FakeWeatherHistoryTracker:
    def __init__(self) -> None:
        self.initialized = False

    async def initialize(self) -> None:
        self.initialized = True


class FakeSessionLeakMonitor:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True


class FakeMetadataStoreAutoUpdater:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True


class FakeDawnResetCoordinator:
    def __init__(self) -> None:
        self.initialized = False

    async def initialize_state(self) -> None:
        self.initialized = True


class FakeJobManager:
    def __init__(self) -> None:
        self.poll_calls = 0
        self.registered_jobs: List[Any] = []

    async def poll(self) -> None:
        self.poll_calls += 1

    async def register_job(self, job: Any) -> None:
        self.registered_jobs.append(job)


class FakePnLManager:
    def __init__(self) -> None:
        self.initialized = False
        self.stopped = False

    async def initialize(self) -> None:
        self.initialized = True

    async def stop(self) -> None:
        self.stopped = True


async def flush_async_callbacks() -> None:
    """
    Advance the event loop once. Useful when the code under test schedules
    background tasks that need a chance to run.
    """

    await asyncio.sleep(0)


__all__ = [
    "FakeAlert",
    "FakeAlerter",
    "FakeHealthCheck",
    "FakeHealthChecker",
    "FakeTrackerController",
    "FakeProcessManager",
    "FakeProcessMonitor",
    "FakeHistoryMetricsRecorder",
    "FakePriceHistoryTracker",
    "FakeWeatherHistoryTracker",
    "FakeSessionLeakMonitor",
    "FakeMetadataStoreAutoUpdater",
    "FakeDawnResetCoordinator",
    "FakeJobManager",
    "FakePnLManager",
    "flush_async_callbacks",
]
