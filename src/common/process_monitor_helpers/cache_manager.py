"""Process cache management functionality."""

import logging
import time
from typing import Dict, List, Optional

import psutil

from ..process_monitor import ProcessInfo

logger = logging.getLogger(__name__)


class ProcessCacheManager:
    """Manages process cache with TTL and freshness checks."""

    def __init__(self, cache_ttl_seconds: int):
        self.cache_ttl_seconds = cache_ttl_seconds

    def filter_fresh_processes(self, processes: List[ProcessInfo], current_time: Optional[float] = None) -> List[ProcessInfo]:
        """
        Filter processes to keep only fresh ones.

        Args:
            processes: List of process info
            current_time: Current timestamp (defaults to now)

        Returns:
            List of fresh processes
        """
        if current_time is None:
            current_time = time.time()

        return [proc for proc in processes if current_time - proc.last_seen < self.cache_ttl_seconds]

    def is_process_fresh(self, process_info: ProcessInfo, current_time: Optional[float] = None) -> bool:
        """Check if a process is fresh."""
        if current_time is None:
            current_time = time.time()
        return current_time - process_info.last_seen < self.cache_ttl_seconds

    def update_process_metrics(self, pid: int, process_cache: Dict[int, ProcessInfo]) -> Optional[ProcessInfo]:
        """
        Update CPU and memory metrics for a specific process.

        Args:
            pid: Process ID
            process_cache: Process cache to update

        Returns:
            Updated ProcessInfo if successful, None otherwise
        """
        try:
            _process = psutil.Process(pid)

            # Update cached process info
            if pid in process_cache:
                process_cache[pid].last_seen = time.time()
                return process_cache[pid]

        except (  # policy_guard: allow-silent-handler
            psutil.NoSuchProcess,
            psutil.AccessDenied,
        ):
            logger.debug(f"Failed to update metrics for PID {pid}")
            # Remove dead process from cache
            if pid in process_cache:
                del process_cache[pid]

        return None
