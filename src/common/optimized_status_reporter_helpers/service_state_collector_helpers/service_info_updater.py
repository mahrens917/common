"""Service info update utilities."""

from typing import Any, Optional

from common.monitoring import ProcessStatus


class ServiceInfoUpdater:
    """Updates service info based on process state."""

    @staticmethod
    def update_from_handle(
        info: Any,
        process_handle: Any,
    ) -> None:
        """
        Update info from process handle.

        Args:
            info: Process info to update
            process_handle: Process handle
        """
        if info.pid != process_handle.pid:
            info.pid = process_handle.pid
        if info.status != ProcessStatus.RUNNING:
            info.status = ProcessStatus.RUNNING

    @staticmethod
    def clear_stopped_process(info: Any) -> None:
        """
        Clear PID and update status for stopped process.

        Args:
            info: Process info to update
        """
        info.pid = None
        if info.status == ProcessStatus.RUNNING:
            info.status = ProcessStatus.STOPPED

    @staticmethod
    def mark_as_running(info: Optional[Any]) -> None:
        """
        Mark service as running.

        Args:
            info: Process info to update
        """
        if info and info.status != ProcessStatus.RUNNING:
            info.status = ProcessStatus.RUNNING
