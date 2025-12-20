from __future__ import annotations

"""Helper for managing chart file lifecycle"""


import logging
import os
from typing import Any

logger = logging.getLogger("src.monitor.chart_generator")


class ChartFileManager:
    """Manages chart file creation and cleanup"""

    def __init__(self, os_module: Any | None = None):
        self._os = os_module or os
        self._os_path = getattr(self._os, "path", os.path)

    def cleanup_chart_files(self, chart_paths: list[str]):
        """
        Clean up temporary chart files

        Args:
            chart_paths: List of file paths to clean up

        Raises:
            RuntimeError: If file not found or cleanup fails
        """
        for file_path in chart_paths:
            if not self._os_path.exists(file_path):
                exc = FileNotFoundError(file_path)
                logger.warning("Chart file not found for cleanup: %s", file_path)
                raise RuntimeError(f"Chart file not found for cleanup: {file_path}") from exc
            try:
                self._os.unlink(file_path)
                logger.debug("Cleaned up chart file: %s", file_path)
            except OSError as exc:
                logger.warning("Failed to clean up chart file %s: %s", file_path, exc)
                raise RuntimeError(f"Failed to clean up chart file {file_path}") from exc

    def cleanup_single_chart_file(self, chart_path: str):
        """
        Clean up a single temporary chart file

        Args:
            chart_path: File path to clean up

        Raises:
            RuntimeError: If file not found or cleanup fails
        """
        if not self._os_path.exists(chart_path):
            exc = FileNotFoundError(chart_path)
            logger.warning("Chart file not found for cleanup: %s", chart_path)
            raise RuntimeError(f"Chart file not found for cleanup: {chart_path}") from exc
        try:
            self._os.unlink(chart_path)
            logger.debug("Cleaned up chart file: %s", chart_path)
        except OSError as exc:
            logger.warning("Failed to clean up chart file %s: %s", chart_path, exc)
            raise RuntimeError(f"Failed to clean up chart file {chart_path}") from exc
