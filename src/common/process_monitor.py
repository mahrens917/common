"""Process monitor access for common utilities."""

from __future__ import annotations

from typing import Any


async def get_global_process_monitor() -> Any:
    """Get the global process monitor instance."""
    from monitor.common_local.process_monitor import get_global_process_monitor as _get

    return await _get()


__all__ = ["get_global_process_monitor"]
