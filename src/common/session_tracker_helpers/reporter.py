"""Session reporting and logging utilities."""

import logging
import time
from typing import List

from src.common.session_tracker_helpers.models import SessionInfo

logger = logging.getLogger(__name__)


class SessionReporter:
    """Generates reports and logs for session tracking."""

    def __init__(self, log_level: int):
        """
        Initialize session reporter.

        Args:
            log_level: Logging level for session tracking messages
        """
        self._log_level = log_level

    def log_summary(self, active_sessions: List[SessionInfo], total_sessions: int) -> None:
        """
        Log summary of all tracked sessions.

        Args:
            active_sessions: List of currently active sessions
            total_sessions: Total number of tracked sessions
        """
        closed_sessions = total_sessions - len(active_sessions)

        logger.log(
            self._log_level,
            f"📊 Session summary: {total_sessions} total, {closed_sessions} closed, "
            f"{len(active_sessions)} active",
        )

        if active_sessions:
            logger.warning(f"⚠️  {len(active_sessions)} sessions still active:")
            for session_info in active_sessions:
                duration = time.time() - session_info.created_at
                last_activity_ago = time.time() - session_info.last_activity
                logger.warning(
                    f"  - {session_info.session_id} ({session_info.service_name}): "
                    f"age={duration:.1f}s, last_activity={last_activity_ago:.1f}s ago, "
                    f"requests={session_info.request_count}"
                )
