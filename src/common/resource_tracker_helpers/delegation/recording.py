"""Recording delegation for ResourceTracker."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..cpu_tracker import CpuTracker
    from ..ram_tracker import RamTracker

logger = logging.getLogger(__name__)


async def record_cpu_usage(cpu_tracker: "CpuTracker", total_cpu_percent: float) -> bool:
    """Record total CPU usage across all processes."""
    return await cpu_tracker.record_cpu_usage(total_cpu_percent)


async def record_ram_usage(ram_tracker: "RamTracker", total_ram_mb: float) -> bool:
    """Record total RAM usage across all processes."""
    return await ram_tracker.record_ram_usage(total_ram_mb)
