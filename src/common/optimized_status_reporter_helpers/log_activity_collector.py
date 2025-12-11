"""
Log activity monitoring and collection.

Gathers log activity status for all services.
"""

import logging
from pathlib import Path
from typing import Dict, List, Tuple

from redis.exceptions import RedisError

from common.health.log_activity_monitor import (
    LOG_ACTIVITY_ERRORS,
    LogActivity,
    LogActivityMonitor,
    LogActivityStatus,
)

logger = logging.getLogger(__name__)


class LogActivityCollector:
    """Collects log activity for all services."""

    def __init__(self, process_manager):
        self.process_manager = process_manager
        project_root = Path(__file__).resolve().parents[3]
        logs_directory = project_root / "logs"
        self._log_activity_monitor = LogActivityMonitor(str(logs_directory))

    async def collect_log_activity_map(
        self,
    ) -> Tuple[Dict[str, LogActivity], List[str]]:
        """Gather log activity for all services and identify stale logs."""
        log_activity: Dict[str, LogActivity] = {}
        try:
            service_names = sorted(set(self.process_manager.services.keys()) | {"monitor"})
            if service_names:
                log_activity = await self._log_activity_monitor.get_all_service_log_activity(service_names)
        except LOG_ACTIVITY_ERRORS + (RedisError,) as exc:
            logger.warning(
                "Failed to gather log activity (%s): %s",
                type(exc).__name__,
                exc,
            )

        stale_logs: List[str] = []
        for service_name, activity in log_activity.items():
            if activity.status in {LogActivityStatus.STALE, LogActivityStatus.OLD}:
                stale_logs.append(service_name)

        return log_activity, stale_logs
