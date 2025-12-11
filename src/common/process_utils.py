from __future__ import annotations

"""Shared helpers for process manager implementations."""

from typing import Any, Dict, Iterable, List, Tuple


def collect_failed_services(process_info: Dict[str, Any], failed_states: Iterable[Any]) -> List[str]:
    """Return service names whose status matches one of the failure states."""
    failed_set = set(failed_states)
    return [name for name, info in process_info.items() if getattr(info, "status", None) in failed_set]


class FailedServiceMixin:
    """Mixin that exposes `get_failed_services` using shared helpers."""

    FAILED_SERVICE_STATES: Tuple[Any, ...] = ()

    def get_failed_services(self) -> List[str]:
        """Return service identifiers whose status is considered failed."""
        if not self.FAILED_SERVICE_STATES:
            raise AttributeError("FAILED_SERVICE_STATES must be set on mixin implementers")
        process_info = getattr(self, "process_info", None)
        if process_info is None:
            return []
        return collect_failed_services(process_info, self.FAILED_SERVICE_STATES)


__all__ = ["collect_failed_services", "FailedServiceMixin"]
