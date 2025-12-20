"""Process rediscovery utilities."""

from __future__ import annotations

from typing import Any, Optional


class ProcessRediscoverer:
    """Rediscovers and validates process state."""

    @staticmethod
    def rediscover_and_validate(
        service_name: str,
        process_manager: Any,
        pid_validator: Any,
    ) -> tuple[bool, Optional[Any]]:
        """
        Rediscover process and validate its state.

        Args:
            service_name: Name of service
            process_manager: Process manager instance
            pid_validator: PID validator instance

        Returns:
            Tuple of (is_running, process_info)
        """
        process_manager._rediscover_process(service_name)
        info = process_manager.process_info.get(service_name)

        if not info or not info.pid:
            return False, info

        is_running = pid_validator.is_running(info.pid)
        return is_running, info
