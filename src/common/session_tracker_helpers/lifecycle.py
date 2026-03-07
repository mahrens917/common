"""Session lifecycle tracking - creation, closure, queries, and helpers."""

import logging
import time
import traceback
import weakref
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import aiohttp

from common.session_tracker_helpers.models import SessionInfo


def get_stack_trace() -> str:
    """Get current stack trace for debugging."""
    return "".join(traceback.format_stack()[-3:-1])


logger = logging.getLogger(__name__)


class SessionLifecycleTracker:
    """Tracks session creation and closure events."""

    def __init__(
        self,
        sessions: Dict[str, SessionInfo],
        session_refs: Dict[str, weakref.ReferenceType],
        log_level: int,
    ):
        """
        Initialize lifecycle tracker.

        Args:
            sessions: Dictionary mapping session IDs to SessionInfo
            session_refs: Dictionary mapping session IDs to weak references
            log_level: Logging level for session tracking messages
        """
        self.sessions = sessions
        self.session_refs = session_refs
        self._log_level = log_level

    def track_creation(self, session: aiohttp.ClientSession, session_id: str, service_name: str) -> SessionInfo:
        """
        Track creation of a new HTTP session.

        Args:
            session: The aiohttp.ClientSession instance
            session_id: Unique session ID
            service_name: Name of the service creating the session

        Returns:
            SessionInfo object for the new session
        """
        created_stack = get_stack_trace()

        session_info = SessionInfo(
            session_id=session_id,
            service_name=service_name,
            created_at=time.time(),
            created_stack=created_stack,
        )

        self.sessions[session_id] = session_info

        logger.log(self._log_level, f"📤 Session created: {session_id} for {service_name}")
        logger.log(self._log_level, f"📤 Session {session_id} creation stack:\n{created_stack}")

        return session_info

    def track_closure(self, session_id: str) -> None:
        """
        Track explicit closure of a session.

        Args:
            session_id: Session ID to mark as closed
        """
        if session_id not in self.sessions:
            return

        session_info = self.sessions[session_id]
        session_info.closed_at = time.time()
        session_info.closed_stack = get_stack_trace()
        session_info.is_closed = True

        duration = session_info.closed_at - session_info.created_at

        logger.log(
            self._log_level,
            f"📥 Session closed: {session_id} for {session_info.service_name} "
            f"(duration: {duration:.1f}s, requests: {session_info.request_count})",
        )
        logger.log(
            self._log_level,
            f"📥 Session {session_id} closure stack:\n{session_info.closed_stack}",
        )


class SessionIdGenerator:
    """Generates unique session IDs for tracking."""

    def __init__(self):
        self._next_session_id = 1

    def generate(self) -> str:
        """Generate unique session ID."""
        session_id = f"session_{self._next_session_id:04d}"
        self._next_session_id += 1
        return session_id


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


class SessionQueries:
    """Provides read-only access to tracked session metadata."""

    def __init__(self, sessions: Dict[str, SessionInfo], session_refs: Dict[str, weakref.ReferenceType]):
        self.sessions = sessions
        self.session_refs = session_refs

    def get_active_sessions(self) -> List[SessionInfo]:
        return [s for s in self.sessions.values() if not s.is_closed]

    def get_total_session_count(self) -> int:
        return len(self.sessions)
