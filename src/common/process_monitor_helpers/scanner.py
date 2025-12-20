"""Process scanning functionality."""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Dict, List

import psutil

from common.truthy import pick_if

from ..process_monitor import ProcessInfo

logger = logging.getLogger(__name__)


class ProcessScanner:
    """Handles full and incremental process scanning."""

    def __init__(self, service_patterns: Dict[str, List[str]]):
        self.service_patterns = service_patterns

    def perform_full_scan(
        self,
    ) -> tuple[Dict[int, ProcessInfo], Dict[str, List[ProcessInfo]], List[ProcessInfo]]:
        logger.debug("Performing full process scan...")
        start_time = time.time()

        new_process_cache = {}
        new_service_cache = defaultdict(list)
        new_redis_processes = []

        try:
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    pid = proc.info["pid"]
                    name_value = proc.info.get("name")
                    name = pick_if(name_value is None, lambda: "", lambda: str(name_value))

                    cmdline_value = proc.info.get("cmdline")
                    cmdline: list[str] = []
                    if isinstance(cmdline_value, list):
                        cmdline = [str(arg) for arg in cmdline_value]

                    process_info = ProcessInfo(pid=pid, name=name, cmdline=cmdline, last_seen=time.time())

                    new_process_cache[pid] = process_info

                    # Check service patterns
                    for service_name, pattern in self.service_patterns.items():
                        if self._matches_service_pattern(cmdline, pattern):
                            new_service_cache[service_name].append(process_info)
                            break

                    # Check Redis
                    if self._is_redis_process(name, cmdline):
                        new_redis_processes.append(process_info)

                except (  # policy_guard: allow-silent-handler
                    psutil.NoSuchProcess,
                    psutil.AccessDenied,
                ):
                    continue

            scan_time = time.time() - start_time
            logger.debug(f"Full process scan completed in {scan_time:.3f}s, cached {len(new_process_cache)} processes")

            return new_process_cache, dict(new_service_cache), new_redis_processes

        except (  # policy_guard: allow-silent-handler
            psutil.Error,
            RuntimeError,
            OSError,
        ):
            logger.exception(f"Error during full process scan: ")
            return {}, {}, []

    def perform_incremental_scan(self, process_cache: Dict[int, ProcessInfo]) -> List[int]:
        logger.debug("Performing incremental process scan...")
        start_time = time.time()

        dead_pids = []
        for pid in list(process_cache.keys()):
            try:
                if not psutil.pid_exists(pid):
                    dead_pids.append(pid)
            except (  # policy_guard: allow-silent-handler
                psutil.Error,
                OSError,
            ):
                dead_pids.append(pid)

        scan_time = time.time() - start_time
        logger.debug(f"Incremental process scan completed in {scan_time:.3f}s, removed {len(dead_pids)} dead processes")

        return dead_pids

    def _matches_service_pattern(self, cmdline: List[str], pattern: List[str]) -> bool:
        if not cmdline:
            return False
        return all(any(expected in str(arg) for arg in cmdline) for expected in pattern)

    def _is_redis_process(self, name: str, cmdline: List[str]) -> bool:
        if "redis-server" in name:
            return True
        if cmdline:
            return any("redis" in str(arg).lower() for arg in cmdline)
        return False

    def matches_service_pattern(self, cmdline: List[str], pattern: List[str]) -> bool:
        return self._matches_service_pattern(cmdline, pattern)

    def is_redis_process(self, name: str, cmdline: List[str]) -> bool:
        return self._is_redis_process(name, cmdline)
