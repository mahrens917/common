"""Monitoring control delegation for ResourceTracker."""

import logging
from typing import Any, Optional

from src.common.redis_protocol.typing import ensure_awaitable

logger = logging.getLogger(__name__)


async def start_per_second_monitoring(monitoring_loop: Any, get_cpu_ram_func) -> None:
    """Start per-second monitoring task."""
    if monitoring_loop is None:
        logger.debug("Per-second monitoring loop missing after initialization")
        return

    start_method = getattr(monitoring_loop, "start", None)
    if callable(start_method):
        await ensure_awaitable(start_method(get_cpu_ram_func))
        return

    if callable(monitoring_loop):
        await ensure_awaitable(monitoring_loop(get_cpu_ram_func))
        return

    logger.error("Monitoring loop missing callable start handler")


async def stop_per_second_monitoring(monitoring_loop: Any) -> None:
    """Stop per-second monitoring task."""
    if monitoring_loop is None:
        return

    stop_method = getattr(monitoring_loop, "stop", None)
    if callable(stop_method):
        await ensure_awaitable(stop_method())


def get_max_cpu_last_minute(monitoring_loop: Any) -> Optional[float]:
    """Get maximum CPU usage over the last minute."""
    if monitoring_loop is None or not hasattr(monitoring_loop, "get_max_cpu_last_minute"):
        return None
    return monitoring_loop.get_max_cpu_last_minute()


def get_max_ram_last_minute(monitoring_loop: Any) -> Optional[float]:
    """Get maximum RAM usage over the last minute."""
    if monitoring_loop is None or not hasattr(monitoring_loop, "get_max_ram_last_minute"):
        return None
    return monitoring_loop.get_max_ram_last_minute()
