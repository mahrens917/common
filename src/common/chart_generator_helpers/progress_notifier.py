from __future__ import annotations

"""Helper for notifying progress callbacks"""


import logging
from typing import Callable, Optional

from ..chart_generator.exceptions import ProgressNotificationError

logger = logging.getLogger("src.monitor.chart_generator")


class ProgressNotifier:
    """Handles progress callback notifications"""

    def __init__(self, progress_callback: Optional[Callable[[str], None]] = None):
        self._progress_callback = progress_callback

    def notify_progress(self, message: str) -> None:
        """
        Notify progress callback with message

        Args:
            message: Progress message to send

        Raises:
            ProgressNotificationError: If callback fails
        """
        if self._progress_callback is None:
            return
        try:
            self._progress_callback(message)
        except (RuntimeError, ValueError, TypeError) as exc:
            logger.debug("Progress callback failed for message: %s", message)
            raise ProgressNotificationError("Progress callback failed") from exc
