"""Metrics reading operations for memory monitoring."""

import asyncio
import logging

import psutil

logger = logging.getLogger(__name__)

PSUTIL_ERRORS = (psutil.Error, OSError)
TASK_QUERY_ERRORS = (RuntimeError, ValueError)


class MetricsReader:
    """Reads current memory, system, and task metrics."""

    def __init__(self, process: psutil.Process):
        """
        Initialize metrics reader.

        Args:
            process: Process handle for memory monitoring
        """
        self.process = process

    def get_current_memory_usage(self) -> float:
        """Get current process memory usage in MB."""
        try:
            memory_info = self.process.memory_info()
            return memory_info.rss / 1024 / 1024  # Convert bytes to MB
        except PSUTIL_ERRORS:  # Expected exception, returning default value  # policy_guard: allow-silent-handler
            logger.warning(f"Failed to get memory usage")
            return 0.0

    def get_system_memory_percent(self) -> float:
        """Get current system memory usage percentage."""
        try:
            return psutil.virtual_memory().percent
        except PSUTIL_ERRORS:  # Expected exception, returning default value  # policy_guard: allow-silent-handler
            logger.warning(f"Failed to get system memory")
            return 0.0

    def get_current_task_count(self) -> int:
        """Get current number of asyncio tasks."""
        try:
            loop = asyncio.get_running_loop()
            return len([task for task in asyncio.all_tasks(loop) if not task.done()])
        except TASK_QUERY_ERRORS:  # Expected exception, returning default value  # policy_guard: allow-silent-handler
            logger.warning(f"Failed to get task count")
            return 0
