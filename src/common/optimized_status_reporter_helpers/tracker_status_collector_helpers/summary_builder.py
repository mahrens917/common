"""Summary building utilities."""

from typing import Any, Dict, Optional


class SummaryBuilder:
    """Builds tracker status summaries."""

    @staticmethod
    def build_running_summary(
        tracker_enabled: bool,
        tracker_pid: Optional[int],
    ) -> str:
        """
        Build summary for running tracker.

        Args:
            tracker_enabled: Whether tracker is enabled
            tracker_pid: Process ID

        Returns:
            Status summary string
        """
        summary_parts = ["🟢 Running"]

        if tracker_enabled:
            summary_parts.append("Enabled")
        else:
            summary_parts.append("Disabled")

        if tracker_pid:
            summary_parts.append(f"pid={tracker_pid}")

        return " | ".join(summary_parts)

    @staticmethod
    def build_stopped_summary(tracker_enabled: bool) -> str:
        """
        Build summary for stopped tracker.

        Args:
            tracker_enabled: Whether tracker is enabled

        Returns:
            Status summary string
        """
        if tracker_enabled:
            return "🔴 Stopped | Enabled"
        return "🔴 Stopped | Disabled"

    @staticmethod
    def update_status_dict(
        tracker_status: Dict[str, Any],
        running: bool,
        pid: Optional[int],
        summary: str,
    ) -> None:
        """
        Update tracker status dictionary.

        Args:
            tracker_status: Status dict to update
            running: Running status
            pid: Process ID
            summary: Status summary
        """
        tracker_status["running"] = running
        tracker_status["pid"] = pid
        tracker_status["status_summary"] = summary
