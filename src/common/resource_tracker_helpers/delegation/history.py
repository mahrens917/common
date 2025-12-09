"""History retrieval delegation for ResourceTracker."""

import logging
from typing import TYPE_CHECKING, List, Tuple

if TYPE_CHECKING:
    from ..cpu_tracker import CpuTracker
    from ..ram_tracker import RamTracker

logger = logging.getLogger(__name__)


async def get_cpu_history(cpu_tracker: "CpuTracker", hours: int = 24) -> List[Tuple[int, float]]:
    """Get CPU usage history.

    Raises:
        Exception: Propagates any errors from the underlying tracker.
    """
    return await cpu_tracker.get_cpu_history(hours)


async def get_ram_history(ram_tracker: "RamTracker", hours: int = 24) -> List[Tuple[int, float]]:
    """Get RAM usage history.

    Raises:
        Exception: Propagates any errors from the underlying tracker.
    """
    return await ram_tracker.get_ram_history(hours)
