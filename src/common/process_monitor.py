"""
Efficient process monitoring system that eliminates CPU spikes from process scanning.

This module provides a centralized, cached process monitoring solution that:
1. Caches process PIDs to avoid expensive psutil.process_iter() calls
2. Provides efficient process lookup and monitoring
3. Eliminates CPU spikes caused by frequent system process scanning

The expensive psutil.process_iter() calls were causing significant CPU spikes
every 60 seconds across multiple monitor components.
"""

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, Iterable, List, Optional

from .process_monitor_mixins import (
    ProcessMonitorCacheMixin,
    ProcessMonitorPatternMixin,
    ProcessMonitorScanMixin,
)

if TYPE_CHECKING:
    from .process_monitor_helpers.dependencies_factory import (
        ProcessMonitorDependencies,
    )

logger = logging.getLogger(__name__)


@dataclass
class ProcessInfo:
    """Cached process information."""

    pid: int
    name: str
    cmdline: List[str]
    last_seen: float


@dataclass
class ServiceProcessInfo:
    """Service-specific process information."""

    service_name: str
    process_info: ProcessInfo
    is_running: bool
    last_updated: float


class _ProcessCacheManager:
    """Stateful cache holder to keep ProcessMonitor lean."""

    def __init__(self, scan_coordinator):
        self._scan_coordinator = scan_coordinator
        self.process_cache: Dict[int, ProcessInfo] = {}
        self.service_cache: Dict[str, List[ProcessInfo]] = defaultdict(list)
        self.redis_processes: List[ProcessInfo] = []
        self.last_full_scan = 0.0

    async def perform_full_scan(self) -> None:
        (
            self.process_cache,
            self.service_cache,
            self.redis_processes,
            self.last_full_scan,
        ) = await self._scan_coordinator.perform_full_scan(
            self.process_cache, self.service_cache, self.redis_processes
        )

    async def perform_incremental_scan(self) -> bool:
        (
            self.process_cache,
            self.service_cache,
            self.redis_processes,
            self.last_full_scan,
            full_scan_triggered,
        ) = await self._scan_coordinator.perform_incremental_scan(
            self.process_cache, self.service_cache, self.redis_processes
        )
        return full_scan_triggered


class ProcessMonitor(
    ProcessMonitorScanMixin,
    ProcessMonitorPatternMixin,
    ProcessMonitorCacheMixin,
):
    """Centralized process monitor backing cached PIDs."""

    def __init__(
        self,
        cache_ttl_seconds: int = 300,
        scan_interval_seconds: int = 60,
        *,
        dependencies: Optional["ProcessMonitorDependencies"] = None,
    ):
        self.cache_ttl_seconds = cache_ttl_seconds
        self.scan_interval_seconds = scan_interval_seconds
        self._shutdown_event = asyncio.Event()
        self._background_task: Optional[asyncio.Task] = None
        if dependencies is None:
            from .process_monitor_helpers.dependencies_factory import (
                ProcessMonitorDependenciesFactory,
            )

            deps = ProcessMonitorDependenciesFactory.create(
                cache_ttl_seconds,
                scan_interval_seconds,
                self._perform_incremental_scan_impl,
                self._shutdown_event,
            )
        else:
            deps = dependencies
        self._scanner = deps.scanner
        self._scan_coordinator = deps.scan_coordinator
        self._background_worker = deps.background_worker
        self._lifecycle = deps.lifecycle
        self._api = deps.api
        self._cache_manager = _ProcessCacheManager(self._scan_coordinator)

    async def initialize(self) -> None:
        """Fully refresh caches before use."""
        await self._perform_full_scan()

    async def start_background_scanning(self) -> None:
        """Spawn the background scan loop."""
        if self._background_task is not None:
            return
        await self.initialize()
        self._shutdown_event.clear()
        self._background_task = asyncio.create_task(self._background_scan_loop())
        logger.info(
            "Started process monitor background scanning (interval: %ss)",
            self.scan_interval_seconds,
        )

    async def stop_background_scanning(self) -> None:
        """Stop the background scan loop."""
        if self._background_task is None:
            return
        logger.info("Stopping process monitor background scanning")
        self._shutdown_event.set()
        try:
            await asyncio.wait_for(self._background_task, timeout=2.0)
        except asyncio.TimeoutError:
            self._background_task.cancel()
        self._background_task = None
        logger.info("Process monitor background scanning stopped")

    async def get_service_processes(self, service_name: str) -> List[ProcessInfo]:
        await self._ensure_cache_fresh()
        return await self._api.get_service_processes(
            service_name, self._cache_manager.service_cache
        )

    async def get_redis_processes(self) -> List[ProcessInfo]:
        await self._ensure_cache_fresh()
        fresh_redis, cache_updated = await self._api.get_redis_processes(
            self._cache_manager.redis_processes
        )
        if cache_updated:
            self._cache_manager.redis_processes = fresh_redis
        return fresh_redis

    async def get_process_by_pid(self, pid: int) -> Optional[ProcessInfo]:
        await self._ensure_cache_fresh()
        return await self._api.get_process_by_pid(pid, self._cache_manager.process_cache)

    async def find_processes_by_keywords(self, keywords: Iterable[str]) -> List[ProcessInfo]:
        await self._ensure_cache_fresh()
        return await self._api.find_processes_by_keywords(
            keywords, self._cache_manager.process_cache
        )

    async def update_process_metrics(self, pid: int) -> Optional[ProcessInfo]:
        return await self._api.update_process_metrics(pid, self._cache_manager.process_cache)

    async def _perform_full_scan(self) -> None:
        await self._cache_manager.perform_full_scan()


_global_process_monitor: Optional[ProcessMonitor] = None


async def get_global_process_monitor() -> ProcessMonitor:
    """Get the singleton process monitor."""
    global _global_process_monitor
    if _global_process_monitor is None:
        _global_process_monitor = ProcessMonitor()
        await _global_process_monitor.initialize()
    return _global_process_monitor


async def get_service_processes(service_name: str) -> List[ProcessInfo]:
    monitor = await get_global_process_monitor()
    return await monitor.get_service_processes(service_name)


async def get_redis_processes() -> List[ProcessInfo]:
    monitor = await get_global_process_monitor()
    return await monitor.get_redis_processes()


async def get_process_by_pid(pid: int) -> Optional[ProcessInfo]:
    monitor = await get_global_process_monitor()
    return await monitor.get_process_by_pid(pid)


async def find_processes_by_keywords(keywords: Iterable[str]) -> List[ProcessInfo]:
    monitor = await get_global_process_monitor()
    return await monitor.find_processes_by_keywords(keywords)
