"""Status normalization utilities."""

from typing import Any, Dict, Optional

from src.common.monitoring import ProcessStatus


class StatusNormalizer:
    """Normalizes tracker status values."""

    @staticmethod
    def normalize_tracker_flags(
        tracker_status: Dict[str, Any],
    ) -> tuple[bool, Optional[bool], Optional[int]]:
        """
        Normalize tracker status flags.

        Args:
            tracker_status: Raw tracker status

        Returns:
            Tuple of (enabled, running, pid)
        """
        # Tracker enabled is True if not explicitly set to False
        tracker_enabled_raw = tracker_status.get("enabled")
        tracker_enabled = tracker_enabled_raw if tracker_enabled_raw is not None else True
        tracker_running_raw = tracker_status.get("running")
        tracker_running = None if tracker_running_raw is None else bool(tracker_running_raw)
        tracker_pid = tracker_status.get("pid")

        return tracker_enabled, tracker_running, tracker_pid

    @staticmethod
    def resolve_running_status(
        tracker_running: Optional[bool],
        tracker_info: Any,
    ) -> Optional[bool]:
        """
        Resolve final running status.

        Args:
            tracker_running: Current running status
            tracker_info: Process info

        Returns:
            Resolved running status
        """
        if tracker_running is not None:
            return tracker_running

        if tracker_info:
            return tracker_info.status == ProcessStatus.RUNNING

        return None
