from __future__ import annotations

"""Shared process lifecycle types used across monitoring components."""


from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ProcessStatus(Enum):
    """Normalized lifecycle states for managed background services."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    FAILED = "failed"
    RESTARTING = "restarting"


@dataclass
class ProcessInfo:
    """Metadata describing a managed process instance."""

    name: str
    module_path: str
    status: ProcessStatus
    pid: Optional[int] = None
    start_time: Optional[float] = None
    exit_code: Optional[int] = None


__all__ = ["ProcessInfo", "ProcessStatus"]
