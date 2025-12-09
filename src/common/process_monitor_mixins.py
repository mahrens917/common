"""Mixin classes for ProcessMonitor functionality."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any, Dict, List

import psutil

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ProcessMonitorScanMixin:
    """Mixin for process scanning operations."""

    _shutdown_event: asyncio.Event
    scan_interval_seconds: int
    _cache_manager: Any
    _scanner: Any

    async def _background_scan_loop(self) -> None:
        while not self._shutdown_event.is_set():
            try:
                await self._perform_incremental_scan()
            except asyncio.CancelledError:
                raise
            except (RuntimeError, ValueError, OSError):
                logger.exception("Background scan loop encountered an error")
            await asyncio.sleep(self.scan_interval_seconds)

    async def _ensure_cache_fresh(self) -> None:
        if time.time() - self._cache_manager.last_full_scan > self.scan_interval_seconds:
            await self._perform_incremental_scan()

    async def _perform_incremental_scan_impl(self) -> bool:
        dead_pids = [
            pid
            for pid in list(self._cache_manager.process_cache.keys())
            if not psutil.pid_exists(pid)
        ]
        for pid in dead_pids:
            self._cache_manager.process_cache.pop(pid, None)
        if dead_pids:
            await self._perform_full_scan()
            return True
        if await self._cache_manager.perform_incremental_scan():
            await self._perform_full_scan()
            return True
        return False

    async def _perform_incremental_scan(self) -> None:
        await self._perform_incremental_scan_impl()

    async def _perform_full_scan(self) -> None:
        """Must be implemented by subclass."""
        raise NotImplementedError


class ProcessMonitorPatternMixin:
    """Mixin for process pattern matching."""

    _scanner: Any

    def matches_service_pattern(self, cmdline: List[str], pattern: List[str]) -> bool:
        return self._scanner.matches_service_pattern(cmdline, pattern)

    def is_redis_process(self, name: str, cmdline: List[str]) -> bool:
        return self._scanner.is_redis_process(name, cmdline)


class ProcessMonitorCacheMixin:
    """Mixin for cache property accessors."""

    _cache_manager: Any

    @property
    def _process_cache(self) -> Dict[int, Any]:
        return self._cache_manager.process_cache

    @_process_cache.setter
    def _process_cache(self, value: Dict[int, Any]) -> None:
        self._cache_manager.process_cache = value

    @property
    def _service_cache(self) -> Dict[str, List[Any]]:
        return self._cache_manager.service_cache

    @_service_cache.setter
    def _service_cache(self, value: Dict[str, List[Any]]) -> None:
        self._cache_manager.service_cache = value

    @property
    def _redis_processes(self) -> List[Any]:
        return self._cache_manager.redis_processes

    @_redis_processes.setter
    def _redis_processes(self, value: List[Any]) -> None:
        self._cache_manager.redis_processes = value

    @property
    def _last_full_scan(self) -> float:
        return self._cache_manager.last_full_scan

    @_last_full_scan.setter
    def _last_full_scan(self, value: float) -> None:
        self._cache_manager.last_full_scan = value


__all__ = [
    "ProcessMonitorScanMixin",
    "ProcessMonitorPatternMixin",
    "ProcessMonitorCacheMixin",
]
