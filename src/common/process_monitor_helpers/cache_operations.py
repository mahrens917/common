"""Cache operations and freshness management."""

import time
from typing import Dict, List, Optional

from ..process_monitor import ProcessInfo


class CacheOperations:
    """Handles cache operations and freshness checks."""

    def __init__(self, cache_ttl_seconds: int):
        self.cache_ttl_seconds = cache_ttl_seconds

    def ensure_service_cache_fresh(
        self,
        service_name: str,
        service_cache: Dict[str, List[ProcessInfo]],
    ) -> List[ProcessInfo]:
        """
        Ensure service cache is fresh, removing stale entries.

        Args:
            service_name: Name of service
            service_cache: Service cache to check

        Returns:
            List of fresh processes
        """
        cached_processes = service_cache.get(service_name) or []
        fresh_processes = self._filter_fresh_processes(cached_processes)

        # Update cache if we filtered out stale processes
        if len(fresh_processes) != len(cached_processes):
            service_cache[service_name] = fresh_processes

        return fresh_processes

    def ensure_redis_cache_fresh(
        self, redis_processes: List[ProcessInfo]
    ) -> tuple[List[ProcessInfo], bool]:
        """
        Ensure Redis cache is fresh.

        Args:
            redis_processes: Current Redis process list

        Returns:
            Tuple of (fresh_processes, cache_updated)
        """
        fresh_redis = self._filter_fresh_processes(redis_processes)
        cache_updated = len(fresh_redis) != len(redis_processes)
        return fresh_redis, cache_updated

    def validate_pid_freshness(
        self, pid: int, process_cache: Dict[int, ProcessInfo]
    ) -> Optional[ProcessInfo]:
        """
        Validate PID exists in cache and is fresh.

        Args:
            pid: Process ID to validate
            process_cache: Process cache to check

        Returns:
            ProcessInfo if found and fresh, None otherwise
        """
        process_info = process_cache.get(pid)
        if process_info is None:
            return None

        # Check if process info is fresh
        if not self._is_process_fresh(process_info):
            del process_cache[pid]
            return None

        return process_info

    def _filter_fresh_processes(self, processes: List[ProcessInfo]) -> List[ProcessInfo]:
        """Filter processes to keep only fresh ones."""
        current_time = time.time()
        return [
            proc for proc in processes if current_time - proc.last_seen < self.cache_ttl_seconds
        ]

    def _is_process_fresh(self, process_info: ProcessInfo) -> bool:
        """Check if a process is fresh."""
        return time.time() - process_info.last_seen < self.cache_ttl_seconds
