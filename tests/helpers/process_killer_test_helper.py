from __future__ import annotations

from types import SimpleNamespace
from typing import Mapping
from unittest.mock import AsyncMock, MagicMock


def create_monitor_mock(processes_by_pid: Mapping[int, SimpleNamespace]):
    monitor = MagicMock()

    async def find_processes_by_keywords(keywords):
        matches = []
        for pid, info in processes_by_pid.items():
            cmdline = getattr(info, "cmdline", None) or []
            joined = " ".join(cmdline)
            if any(keyword in joined for keyword in keywords):
                matches.append(SimpleNamespace(pid=pid, **info.__dict__))
        return matches

    monitor.find_processes_by_keywords = AsyncMock(side_effect=find_processes_by_keywords)
    return monitor
