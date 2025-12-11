"""
Service state collection and validation.

Discovers running services, validates PIDs, and normalizes process states.
"""

import logging
from typing import Dict, List, Optional

from common.monitoring import ProcessStatus

from .service_state_collector_helpers import (
    PidValidator,
    ProcessRediscoverer,
    ServiceInfoUpdater,
)

logger = logging.getLogger(__name__)


class ServiceStateCollector:
    """Collects and validates service process states."""

    def __init__(self, process_manager):
        self.process_manager = process_manager

    async def collect_running_services(self) -> List[Dict[str, str]]:
        running_services: List[Dict[str, str]] = []
        for service_name in self.process_manager.services:
            if self._check_service_status(service_name, PidValidator, ProcessRediscoverer, ServiceInfoUpdater):
                running_services.append({"name": service_name})
        return running_services

    def _check_service_status(
        self,
        service_name: str,
        pid_validator,
        rediscoverer,
        updater,
    ) -> bool:
        info = self.process_manager.process_info.get(service_name)
        if info and not isinstance(info.status, ProcessStatus):
            raise TypeError(
                f"Service {service_name} has invalid status type {type(info.status)}: {info.status}. " "Expected ProcessStatus enum."
            )
        is_running = self._check_process_handle(service_name, info, updater)
        if is_running:
            return True
        is_running, info = rediscoverer.rediscover_and_validate(service_name, self.process_manager, pid_validator)
        if not is_running and info:
            updater.clear_stopped_process(info)
        elif is_running:
            updater.mark_as_running(info)
        return is_running

    def _check_process_handle(self, service_name: str, info, updater) -> bool:
        process_handle = self.process_manager.processes.get(service_name) if hasattr(self.process_manager, "processes") else None
        is_running = bool(process_handle and process_handle.poll() is None)
        if is_running and info and process_handle is not None:
            updater.update_from_handle(info, process_handle)
        return is_running

    async def resolve_redis_pid(self, process_monitor) -> Optional[int]:
        redis_processes = await process_monitor.get_redis_processes()
        if not redis_processes:
            return None
        return redis_processes[0].pid
