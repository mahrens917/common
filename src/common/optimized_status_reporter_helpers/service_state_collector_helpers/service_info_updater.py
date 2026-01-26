"""Service info update utilities.

NOTE: These methods are intentionally no-ops. ProcessInfo should only be
modified by the ProcessManager via psutil probing, not by status reporters.
Status reporters are read-only collectors that gather info for display purposes.
"""

from typing import Any, Optional


class ServiceInfoUpdater:
    """Updates service info based on process state.

    NOTE: All methods are no-ops. ProcessInfo must only be modified by
    the ProcessManager to avoid race conditions and spurious restarts.
    """

    @staticmethod
    def update_from_handle(
        info: Any,
        process_handle: Any,
    ) -> None:
        """
        Update info from process handle.

        NOTE: No-op. ProcessInfo should only be modified by ProcessManager.

        Args:
            info: Process info to update
            process_handle: Process handle
        """
        # Do NOT modify ProcessInfo here - causes race conditions with ProcessManager

    @staticmethod
    def clear_stopped_process(info: Any) -> None:
        """
        Clear PID and update status for stopped process.

        NOTE: No-op. ProcessInfo should only be modified by ProcessManager.

        Args:
            info: Process info to update
        """
        # Do NOT modify ProcessInfo here - causes race conditions with ProcessManager

    @staticmethod
    def mark_as_running(info: Optional[Any]) -> None:
        """
        Mark service as running.

        NOTE: No-op. ProcessInfo should only be modified by ProcessManager.

        Args:
            info: Process info to update
        """
        # Do NOT modify ProcessInfo here - causes race conditions with ProcessManager
