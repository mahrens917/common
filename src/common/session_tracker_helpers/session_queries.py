"""Query helpers for session tracker diagnostics."""

import weakref
from typing import Dict, List

from .models import SessionInfo


class SessionQueries:
    """Provides read-only access to tracked session metadata."""

    def __init__(self, sessions: Dict[str, SessionInfo], session_refs: Dict[str, weakref.ReferenceType]):
        self.sessions = sessions
        self.session_refs = session_refs

    def get_active_sessions(self) -> List[SessionInfo]:
        active_sessions: List[SessionInfo] = []
        for session_info in self.sessions.values():
            if session_info.is_closed:
                continue
            active_sessions.append(session_info)
        return active_sessions

    def get_total_session_count(self) -> int:
        return len(self.sessions)
