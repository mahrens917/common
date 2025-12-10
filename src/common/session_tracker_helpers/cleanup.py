"""Session record cleanup utilities."""

import logging
import time
import weakref
from typing import Dict

from common.session_tracker_helpers.models import SessionInfo

logger = logging.getLogger(__name__)


class SessionCleanup:
    """Manages cleanup of old session records."""

    def __init__(
        self,
        sessions: Dict[str, SessionInfo],
        session_refs: Dict[str, weakref.ReferenceType],
        log_level: int,
    ):
        """
        Initialize session cleanup.

        Args:
            sessions: Dictionary mapping session IDs to SessionInfo
            session_refs: Dictionary mapping session IDs to weak references
            log_level: Logging level for session tracking messages
        """
        self.sessions = sessions
        self.session_refs = session_refs
        self._log_level = log_level

    def cleanup_old_records(self, max_age_seconds: float = 3600) -> None:
        """
        Clean up tracking records for old closed sessions.

        Args:
            max_age_seconds: Maximum age for keeping closed session records
        """
        current_time = time.time()
        to_remove = []

        for session_id, session_info in self.sessions.items():
            if session_info.is_closed and session_info.closed_at:
                age = current_time - session_info.closed_at
                if age > max_age_seconds:
                    to_remove.append(session_id)

        for session_id in to_remove:
            del self.sessions[session_id]
            if session_id in self.session_refs:
                del self.session_refs[session_id]

        if to_remove:
            logger.log(self._log_level, f"🧹 Cleaned up {len(to_remove)} old session records")
