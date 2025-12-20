"""Public API methods for ProcessMonitor."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from ..process_monitor import ProcessInfo


class PublicAPI:
    """Encapsulates public API methods for process lookups."""

    def __init__(self, cache_ops, process_lookup, cache_ttl_seconds: int):
        self.cache_ops = cache_ops
        self.process_lookup = process_lookup
        self.cache_ttl_seconds = cache_ttl_seconds

    async def get_service_processes(self, service_name: str, service_cache: Dict[str, List[ProcessInfo]]) -> List[ProcessInfo]:
        """Get processes for a specific service (non-blocking, cached)."""
        return self.cache_ops.ensure_service_cache_fresh(service_name, service_cache)

    async def get_redis_processes(self, redis_processes: List[ProcessInfo]) -> tuple[List[ProcessInfo], bool]:
        """
        Get Redis server processes (non-blocking, cached).

        Returns:
            Tuple of (fresh_processes, cache_updated)
        """
        return self.cache_ops.ensure_redis_cache_fresh(redis_processes)

    async def get_process_by_pid(self, pid: int, process_cache: Dict[int, ProcessInfo]) -> Optional[ProcessInfo]:
        """Get process information by PID (non-blocking, cached)."""
        return self.cache_ops.validate_pid_freshness(pid, process_cache)

    async def find_processes_by_keywords(self, keywords: Iterable[str], process_cache: Dict[int, ProcessInfo]) -> List[ProcessInfo]:
        """Return processes whose command line contains any of the supplied keywords."""
        return self.process_lookup.find_by_keywords(process_cache, keywords)

    async def update_process_metrics(self, pid: int, process_cache: Dict[int, ProcessInfo]) -> Optional[ProcessInfo]:
        """Update CPU and memory metrics for a specific process."""
        from .cache_manager import ProcessCacheManager

        cache_manager = ProcessCacheManager(self.cache_ttl_seconds)
        return cache_manager.update_process_metrics(pid, process_cache)
