"""
Tracker service status collection and normalization.

Handles tracker-specific status gathering and state merging.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from common.monitoring import ProcessStatus

logger = logging.getLogger(__name__)

TRACKER_STATUS_ERRORS = (
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    RuntimeError,
)


class TrackerStatusCollector:
    """Collects and normalizes tracker service status."""

    def __init__(self, process_manager, tracker_controller):
        self.process_manager = process_manager
        self.tracker_controller = tracker_controller

    async def collect_tracker_status(self) -> Dict[str, Any]:
        """Gather tracker-specific status information."""
        from .tracker_status_collector_helpers import StatusNormalizer

        # Fetch tracker status
        tracker_status = await self._fetch_tracker_status()

        # Normalize status flags
        tracker_enabled, tracker_running, tracker_pid = StatusNormalizer.normalize_tracker_flags(tracker_status)

        # Get tracker info and resolve running status
        tracker_info = self.process_manager.process_info.get("tracker")
        tracker_running = StatusNormalizer.resolve_running_status(tracker_running, tracker_info)

        # Update tracker info if available
        if tracker_info:
            self._update_tracker_info(
                tracker_info,
                tracker_running,
                tracker_pid,
                tracker_enabled,
                tracker_status,
            )

        return tracker_status

    async def _fetch_tracker_status(self) -> Dict[str, Any]:
        """Fetch tracker status from controller."""
        if not self.tracker_controller:
            return {}

        try:
            return await self.tracker_controller.get_tracker_status()
        except TRACKER_STATUS_ERRORS as exc:  # policy_guard: allow-silent-handler
            logger.exception(
                "Failed to get tracker status (%s)",
                type(exc).__name__,
            )
            return {"error": str(exc)}

    def _update_tracker_info(
        self,
        tracker_info,
        tracker_running: Optional[bool],
        tracker_pid: Optional[int],
        tracker_enabled: bool,
        tracker_status: Dict[str, Any],
    ) -> None:
        """Update tracker info based on status."""
        from .tracker_status_collector_helpers import SummaryBuilder

        if tracker_running:
            tracker_info.status = ProcessStatus.RUNNING
            if tracker_pid:
                tracker_info.pid = tracker_pid

            summary = SummaryBuilder.build_running_summary(tracker_enabled, tracker_info.pid)
            SummaryBuilder.update_status_dict(tracker_status, True, tracker_info.pid, summary)
        else:
            tracker_info.status = ProcessStatus.STOPPED
            tracker_info.pid = None

            summary = SummaryBuilder.build_stopped_summary(tracker_enabled)
            SummaryBuilder.update_status_dict(tracker_status, False, None, summary)

    def merge_tracker_service_state(
        self,
        running_services: List[Dict[str, str]],
        tracker_status: Dict[str, Any],
    ) -> List[Dict[str, str]]:
        """Normalize tracker state in running services list."""
        tracker_running = bool(tracker_status.get("running") or False)
        normalized = [svc for svc in running_services if svc.get("name") != "tracker"]
        if tracker_running:
            normalized.append({"name": "tracker"})
        return normalized
