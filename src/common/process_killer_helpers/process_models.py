from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass
class NormalizedProcessCandidate:
    """Concrete process candidate that satisfies the shared protocol."""

    pid: int
    name: str | None
    cmdline: Sequence[str]


class ProcessCandidate(Protocol):
    """Minimal contract for process candidates returned by the monitor."""

    pid: int
    name: str | None
    cmdline: Sequence[str]
