"""
Process health monitoring with single responsibility: "Is the process running?"

Uses the existing ProcessMonitor infrastructure but provides a clean interface
focused solely on process lifecycle status.
"""

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

try:  # pragma: no cover - optional dependency
    import psutil
except ImportError:  # pragma: no cover - psutil not available in some environments
    psutil = None

from ..process_monitor import get_global_process_monitor

logger = logging.getLogger(__name__)

PSUTIL_ERRORS = (psutil.Error,) if psutil else ()
PROCESS_MONITOR_ERRORS = (
    RuntimeError,
    OSError,
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
) + PSUTIL_ERRORS


class ProcessStatus(Enum):
    """Clear process lifecycle states"""

    RUNNING = "running"
    STOPPED = "stopped"
    NOT_FOUND = "not_found"


@dataclass
class ProcessHealthInfo:
    """Process health information"""

    status: ProcessStatus
    pid: Optional[int] = None
    memory_percent: Optional[float] = None
    last_seen: Optional[float] = None


class ProcessHealthMonitor:
    """
    Single responsibility: Monitor process lifecycle status.

    Uses existing ProcessMonitor infrastructure but provides clean interface
    focused only on "is the process running?" question.
    """

    def __init__(self):
        self._process_monitor = None

    async def _get_process_monitor(self):
        """Get global process monitor instance"""
        if self._process_monitor is None:
            self._process_monitor = await get_global_process_monitor()
        return self._process_monitor

    async def get_process_status(self, service_name: str) -> ProcessHealthInfo:
        """
        Get process health status for a service.

        Args:
            service_name: Name of the service to check

        Returns:
            ProcessHealthInfo with clear status
        """
        try:
            monitor = await self._get_process_monitor()
            processes = await monitor.get_service_processes(service_name)

            if not processes:
                return ProcessHealthInfo(status=ProcessStatus.NOT_FOUND)

            # Use the first (most recent) process if multiple found
            process_info = processes[0]

            if psutil is None:
                return ProcessHealthInfo(
                    status=ProcessStatus.RUNNING,
                    pid=process_info.pid,
                    memory_percent=None,
                    last_seen=process_info.last_seen,
                )

            try:
                proc = psutil.Process(process_info.pid)
                if proc.is_running():
                    memory_percent = proc.memory_percent()
                    return ProcessHealthInfo(
                        status=ProcessStatus.RUNNING,
                        pid=process_info.pid,
                        memory_percent=memory_percent,
                        last_seen=process_info.last_seen,
                    )
                return ProcessHealthInfo(status=ProcessStatus.STOPPED)

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
            ):
                return ProcessHealthInfo(status=ProcessStatus.STOPPED)

        except PROCESS_MONITOR_ERRORS:
            logger.exception(f"Error checking process status for : ")
            return ProcessHealthInfo(status=ProcessStatus.NOT_FOUND)

    async def get_all_service_process_status(self, service_names: list[str]) -> Dict[str, ProcessHealthInfo]:
        """
        Get process status for multiple services efficiently.

        Args:
            service_names: List of service names to check

        Returns:
            Dictionary mapping service name to ProcessHealthInfo
        """
        results = {}

        # Get all process statuses concurrently
        tasks = [self.get_process_status(service_name) for service_name in service_names]

        process_results = await asyncio.gather(*tasks, return_exceptions=True)

        for service_name, result in zip(service_names, process_results):
            if isinstance(result, Exception):
                logger.error(f"Error getting process status for {service_name}: {result}")
                results[service_name] = ProcessHealthInfo(status=ProcessStatus.NOT_FOUND)
            else:
                results[service_name] = result

        return results
