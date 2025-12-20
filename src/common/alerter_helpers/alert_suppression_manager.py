"""Alert suppression logic during shutdown."""

import logging
from typing import Set

from common.config import ConfigurationError
from ..helpers.runtime_paths import get_shutdown_flag_path
from ..settings import get_monitor_settings

logger = logging.getLogger(__name__)


class AlertSuppressionManager:
    """Manages alert suppression during graceful shutdown."""

    SHUTDOWN_SUPPRESSED_TYPES: Set[str] = {
        "process_status",
        "error_log_report",
        "message_metrics",
        "stale_log",
    }

    def should_suppress_alert(self, alert_type: str) -> bool:
        """
        Check if alert should be suppressed during shutdown.

        Args:
            alert_type: Type of alert to check

        Returns:
            True if alert should be suppressed
        """
        if not self.is_shutdown_in_progress():
            return False

        if alert_type in self.SHUTDOWN_SUPPRESSED_TYPES:
            logger.info(f"Suppressing '{alert_type}' alert during shutdown")
            return True

        return False

    def is_shutdown_in_progress(self) -> bool:
        """Public helper so other components can react gracefully to shutdown."""
        return self._is_shutdown_in_progress()

    def _is_shutdown_in_progress(self) -> bool:
        """Check if shutdown is in progress via config or flag file."""
        try:
            shutdown_flag = get_monitor_settings().features.shutdown_in_progress
        except ConfigurationError:
            shutdown_flag = False

        if not shutdown_flag:
            shutdown_flag = get_shutdown_flag_path().exists()

        return shutdown_flag
