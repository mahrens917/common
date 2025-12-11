"""Filter helpers for process killer."""

from __future__ import annotations

from typing import Iterable, List, Optional, Protocol, TypeVar


class _ProcessWithPID(Protocol):
    pid: Optional[int]


_ProcessLike = TypeVar("_ProcessLike", bound=_ProcessWithPID)


def filter_processes_by_pid(processes: Iterable[_ProcessLike], exclude_pid: Optional[int]) -> List[_ProcessLike]:
    """Return all processes except those matching the excluded PID."""
    if exclude_pid is None:
        return list(processes)
    return [proc for proc in processes if proc.pid != exclude_pid]
