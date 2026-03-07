"""
Service state collection and validation.

Discovers running services, validates PIDs, and normalizes process states.
"""

import logging
from typing import Any, Dict, List, Optional

import psutil

from common.monitoring import ProcessStatus

logger = logging.getLogger(__name__)


def is_running(pid: int) -> bool:
    """Check if PID is running and not a zombie."""
    try:
        ps_process = psutil.Process(pid)
        return ps_process.is_running() and ps_process.status() != psutil.STATUS_ZOMBIE
    except (  # policy_guard: allow-silent-handler
        psutil.NoSuchProcess,
        psutil.AccessDenied,
        psutil.ZombieProcess,
    ):
        return False


def rediscover_and_validate(
    service_name: str,
    process_manager: Any,
) -> tuple[bool, Optional[Any]]:
    """Rediscover process and validate its state. Returns (is_running, process_info)."""
    process_manager._rediscover_process(service_name)  # pyright: ignore[reportPrivateUsage]
    info = process_manager.process_info.get(service_name)
    if not info or not info.pid:
        return False, info
    return is_running(info.pid), info


def update_from_handle(info: Any, process_handle: Any) -> None:
    """No-op. ProcessInfo should only be modified by ProcessManager."""


def clear_stopped_process(info: Any) -> None:
    """No-op. ProcessInfo should only be modified by ProcessManager."""


def mark_as_running(info: Optional[Any]) -> None:
    """No-op. ProcessInfo should only be modified by ProcessManager."""


class ServiceStateCollector:
    """Collects and validates service process states."""

    def __init__(self, process_manager):
        self.process_manager = process_manager

    async def collect_running_services(self) -> List[Dict[str, str]]:
        running_services: List[Dict[str, str]] = []
        for service_name in self.process_manager.services:
            if self._check_service_status(service_name):
                running_services.append({"name": service_name})
        return running_services

    def _check_service_status(self, service_name: str) -> bool:
        info = self.process_manager.process_info.get(service_name)
        if info and not isinstance(info.status, ProcessStatus):
            raise TypeError(
                f"Service {service_name} has invalid status type {type(info.status)}: {info.status}. " "Expected ProcessStatus enum."
            )
        is_running = self._check_process_handle(service_name, info)
        if is_running:
            return True
        running, info = rediscover_and_validate(service_name, self.process_manager)
        if not running and info:
            clear_stopped_process(info)
        elif running:
            mark_as_running(info)
        return running

    def _check_process_handle(self, service_name: str, info) -> bool:
        process_handle = self.process_manager.processes.get(service_name) if hasattr(self.process_manager, "processes") else None
        is_running = bool(process_handle and process_handle.poll() is None)
        if is_running and info and process_handle is not None:
            update_from_handle(info, process_handle)
        return is_running

    async def resolve_redis_pid(self, process_monitor) -> Optional[int]:
        redis_processes = await process_monitor.get_redis_processes()
        if not redis_processes:
            return None
        return redis_processes[0].pid
