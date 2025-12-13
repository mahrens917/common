"""
Process resource usage tracking.

Monitors RAM usage for service processes.
"""

import logging

import psutil

logger = logging.getLogger(__name__)


class ProcessResourceTracker:
    """Tracks resource usage for service processes."""

    def __init__(self, process_manager):
        self.process_manager = process_manager

    def get_process_resource_usage(self, service_name: str) -> str:
        """
        Get RAM usage for a specific service process.

        Args:
            service_name: Name of the service

        Returns:
            String with resource usage info (e.g., " RAM: 1.8%")
        """
        try:
            # Get PID from process manager
            service_info = self.process_manager.process_info.get(service_name)
            if not service_info or service_info.pid is None:
                return ""

            service_pid = service_info.pid

            # Get process resource usage
            process = psutil.Process(service_pid)
            memory_percent = process.memory_percent()

        except (  # policy_guard: allow-silent-handler
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
            psutil.Error,
            RuntimeError,
        ):
            # Process may have died or we don't have access - return empty string
            return ""
        else:
            return f" RAM: {memory_percent:.1f}%"
