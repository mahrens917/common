"""Tracks activity for tracked sessions."""

import logging
import time
from typing import Dict

from .models import SessionInfo

logger = logging.getLogger(__name__)


class SessionActivityTracker:
    """Records activity events per session."""

    def __init__(self, sessions: Dict[str, SessionInfo], log_level: int):
        self.sessions = sessions
        self._log_level = log_level

    def track_activity(self, session_id: str) -> None:
        session_info = self.sessions.get(session_id)
        if not session_info:
            logger.warning("Activity for unknown session: %s", session_id)
            return
        session_info.request_count += 1
        session_info.last_activity = time.time()
