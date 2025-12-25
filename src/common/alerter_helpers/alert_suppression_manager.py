"""Alert suppression logic during shutdown."""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Set

logger = logging.getLogger(__name__)

_SHUTDOWN_MARKER_NAME = "monitor_shutdown_in_progress"


def _get_runtime_directory() -> Path:
    """Return directory used for runtime markers; allows override via env."""
    override = os.environ.get("MONITOR_RUNTIME_DIR")
    if override:
        return Path(override)
    return Path(tempfile.gettempdir())


def _get_shutdown_flag_path() -> Path:
    """Return full path to the shutdown flag marker."""
    return _get_runtime_directory() / _SHUTDOWN_MARKER_NAME


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
        """Check if shutdown is in progress via env var or flag file."""
        shutdown_value = os.environ.get("SHUTDOWN_IN_PROGRESS")
        shutdown_flag = shutdown_value is not None and shutdown_value.lower() == "true"

        if not shutdown_flag:
            shutdown_flag = _get_shutdown_flag_path().exists()

        return shutdown_flag
