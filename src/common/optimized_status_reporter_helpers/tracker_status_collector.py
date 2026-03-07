"""
Tracker service status collection and normalization.

Handles tracker-specific status gathering and state merging.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from common.monitoring import ProcessStatus
from common.truthy import pick_if, pick_truthy

logger = logging.getLogger(__name__)


class StatusNormalizer:
    """Normalizes tracker status values."""

    @staticmethod
    def normalize_tracker_flags(
        tracker_status: Dict[str, Any],
    ) -> tuple[bool, Optional[bool], Optional[int]]:
        tracker_enabled_raw = tracker_status.get("enabled")
        tracker_enabled = pick_if(tracker_enabled_raw is None, lambda: True, lambda: bool(tracker_enabled_raw))
        tracker_running_raw = tracker_status.get("running")
        tracker_running = None if tracker_running_raw is None else bool(tracker_running_raw)
        tracker_pid_raw = tracker_status.get("pid")
        tracker_pid = tracker_pid_raw if isinstance(tracker_pid_raw, int) else None
        return tracker_enabled, tracker_running, tracker_pid

    @staticmethod
    def resolve_running_status(tracker_running: Optional[bool], tracker_info: Any) -> Optional[bool]:
        if tracker_running is not None:
            return tracker_running
        if tracker_info:
            return tracker_info.status == ProcessStatus.RUNNING
        return None


class SummaryBuilder:
    """Builds tracker status summaries."""

    @staticmethod
    def build_running_summary(tracker_enabled: bool, tracker_pid: Optional[int]) -> str:
        summary_parts = ["🟢 Running"]
        summary_parts.append(pick_if(tracker_enabled, lambda: "Enabled", lambda: "Disabled"))
        if tracker_pid:
            summary_parts.append(f"pid={tracker_pid}")
        return " | ".join(summary_parts)

    @staticmethod
    def build_stopped_summary(tracker_enabled: bool) -> str:
        return pick_if(tracker_enabled, lambda: "🔴 Stopped | Enabled", lambda: "🔴 Stopped | Disabled")

    @staticmethod
    def update_status_dict(tracker_status: Dict[str, Any], running: bool, pid: Optional[int], summary: str) -> None:
        tracker_status["running"] = running
        tracker_status["pid"] = pid
        tracker_status["status_summary"] = summary


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
        except TRACKER_STATUS_ERRORS as exc:  # Expected exception in operation  # policy_guard: allow-silent-handler
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
        # NOTE: Do NOT modify tracker_info.status or tracker_info.pid here.
        # ProcessInfo should only be modified by the process manager.
        if tracker_running:
            summary = SummaryBuilder.build_running_summary(tracker_enabled, tracker_info.pid)
            SummaryBuilder.update_status_dict(tracker_status, True, tracker_info.pid, summary)
        else:
            summary = SummaryBuilder.build_stopped_summary(tracker_enabled)
            SummaryBuilder.update_status_dict(tracker_status, False, None, summary)

    def merge_tracker_service_state(
        self,
        running_services: List[Dict[str, str]],
        tracker_status: Dict[str, Any],
    ) -> List[Dict[str, str]]:
        """Normalize tracker state in running services list."""
        tracker_running = bool(pick_truthy(tracker_status.get("running"), False))
        normalized = [svc for svc in running_services if svc.get("name") != "tracker"]
        if tracker_running:
            normalized.append({"name": "tracker"})
        return normalized
