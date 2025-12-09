"""Helpers for querying the shared process monitor."""

from __future__ import annotations

from typing import Iterable, List

from .. import process_monitor as process_monitor_module
from ..process_monitor import ProcessInfo


async def query_monitor_for_processes(
    process_keywords: Iterable[str], service_name: str
) -> List[ProcessInfo]:
    """Return processes whose command line contains any of the supplied keywords."""
    monitor = await process_monitor_module.get_global_process_monitor()
    candidates = await monitor.find_processes_by_keywords(process_keywords)
    return list(candidates)
