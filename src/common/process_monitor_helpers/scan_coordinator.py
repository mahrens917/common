"""Scan coordination logic."""

from __future__ import annotations

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List

from ..process_monitor import ProcessInfo
from .scanner import ProcessScanner

logger = logging.getLogger(__name__)

_FULL_SCAN_TIMEOUT_SECONDS = 5.0
_PROCESS_SCAN_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="process-scan")


class ScanCoordinator:
    """Coordinates full and incremental scans with threshold-based decisions."""

    def __init__(self, scanner: ProcessScanner, dead_process_threshold: float = 0.1):
        self.scanner = scanner
        self.dead_process_threshold = dead_process_threshold

    async def perform_full_scan(
        self,
        process_cache: Dict[int, ProcessInfo],
        service_cache: Dict[str, List[ProcessInfo]],
        redis_processes: List[ProcessInfo],
    ) -> tuple[Dict[int, ProcessInfo], Dict[str, List[ProcessInfo]], List[ProcessInfo], float]:
        """
        Perform full system process scan.

        Args:
            process_cache: Process cache to update
            service_cache: Service cache to update
            redis_processes: Redis process list to update

        Returns:
            Tuple of (updated_process_cache, updated_service_cache, updated_redis_processes, timestamp)
        """
        _ = process_cache, service_cache, redis_processes
        try:
            loop = asyncio.get_running_loop()
            future = loop.run_in_executor(_PROCESS_SCAN_EXECUTOR, self.scanner.perform_full_scan)
            new_process_cache, new_service_cache, new_redis_processes = await asyncio.wait_for(
                future,
                timeout=_FULL_SCAN_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:  # policy_guard: allow-silent-handler
            logger.exception("Full process scan timed out")
            return {}, {}, [], time.time()
        else:
            return new_process_cache, new_service_cache, new_redis_processes, time.time()

    async def perform_incremental_scan(
        self,
        process_cache: Dict[int, ProcessInfo],
        service_cache: Dict[str, List[ProcessInfo]],
        redis_processes: List[ProcessInfo],
    ) -> tuple[
        Dict[int, ProcessInfo],
        Dict[str, List[ProcessInfo]],
        List[ProcessInfo],
        float,
        bool,
    ]:
        """
        Perform incremental scan to update existing processes.

        Args:
            process_cache: Current process cache
            service_cache: Current service cache
            redis_processes: Current redis process list

        Returns:
            Tuple of (process_cache, service_cache, redis_processes, timestamp, full_scan_triggered)
        """
        dead_pids = self.scanner.perform_incremental_scan(process_cache)

        # Remove dead processes from cache
        for pid in dead_pids:
            if pid in process_cache:
                del process_cache[pid]

        # If we lost too many processes, do a full scan
        full_scan_triggered = False
        if len(process_cache) > 0 and len(dead_pids) > len(process_cache) * self.dead_process_threshold:
            logger.info(f"Too many dead processes ({len(dead_pids)}/{len(process_cache)}), triggering full scan")
            full_scan_triggered = True

        return process_cache, service_cache, redis_processes, time.time(), full_scan_triggered
