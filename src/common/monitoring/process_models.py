from __future__ import annotations

"""Shared process lifecycle types used across monitoring components."""

import logging
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

_logger = logging.getLogger(__name__)


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

    def __setattr__(self, key, value):
        if key == "status" and getattr(self, "name", None) == "tracker":
            old_value = getattr(self, "status", None)
            if old_value != value:
                stack = "".join(traceback.format_stack()[-6:-1])
                _logger.warning("DEBUG PROCESSINFO: tracker status changing from %s to %s\nStack:\n%s", old_value, value, stack)
        super().__setattr__(key, value)


__all__ = ["ProcessInfo", "ProcessStatus"]
