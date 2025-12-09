"""PID validation utilities."""

import psutil


class PidValidator:
    """Validates process PIDs using psutil."""

    @staticmethod
    def is_running(pid: int) -> bool:
        """
        Check if PID is running and not a zombie.

        Args:
            pid: Process ID to check

        Returns:
            True if process is running and not zombie
        """
        try:
            ps_process = psutil.Process(pid)
            return ps_process.is_running() and ps_process.status() != psutil.STATUS_ZOMBIE
        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
        ):
            return False
