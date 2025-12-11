"""Session lifecycle tracking - creation and closure."""

import logging
import time
import weakref
from typing import Dict

import aiohttp

from common.session_tracker_helpers.models import SessionInfo
from common.session_tracker_helpers.stack_tracer import get_stack_trace

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
