"""Normalize process entries returned by the process monitor."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from ..process_monitor import ProcessInfo


@dataclass
class NormalizedProcess:
    pid: int | None
    name: str | None
    cmdline: Sequence[str]


def normalize_process(raw: Any, service_name: str) -> NormalizedProcess:
    """Convert ProcessInfo or dict payloads into a normalized process representation."""
    if isinstance(raw, NormalizedProcess):
        return raw
    if isinstance(raw, ProcessInfo):
        return _normalized_from_process_info(raw)
    if isinstance(raw, dict):
        return _normalized_from_dict(raw, service_name)
    if isinstance(raw, (str, bytes)):
        raise TypeError("Unsupported process payload")
    if isinstance(raw, Sequence):
        raise TypeError("Unsupported process payload")
    return _normalized_from_any(raw)


def _normalized_from_process_info(raw: ProcessInfo) -> NormalizedProcess:
    return NormalizedProcess(pid=raw.pid, name=raw.name, cmdline=raw.cmdline)


def _normalized_from_dict(raw: dict[str, Any], service_name: str) -> NormalizedProcess:
    pid_value = raw.get("pid")
    if pid_value is None:
        raise ValueError(f"Missing pid in process payload for {service_name}: {raw!r}")
    return NormalizedProcess(
        pid=int(pid_value),
        name=raw.get("name"),
        cmdline=raw.get("cmdline") or [],
    )


def _normalized_from_any(raw: Any) -> NormalizedProcess:
    pid_value = getattr(raw, "pid", None)
    pid = int(pid_value) if pid_value is not None else None
    return NormalizedProcess(
        pid=pid,
        name=getattr(raw, "name", None),
        cmdline=getattr(raw, "cmdline", None) or [],
    )
