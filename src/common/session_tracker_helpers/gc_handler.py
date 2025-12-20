"""Generational GC handler for session references."""

from __future__ import annotations

import logging
import weakref
from typing import Dict

from common.session_tracker_helpers.models import SessionInfo

logger = logging.getLogger(__name__)


class GarbageCollectionHandler:
    """Tracks garbage collection callbacks for session references."""

    def __init__(
        self,
        sessions: Dict[str, SessionInfo],
        session_refs: Dict[str, weakref.ReferenceType],
        log_level: int,
    ):
        self.sessions = sessions
        self.session_refs = session_refs
        self._log_level = log_level
        logger.setLevel(log_level)

    def create_callback(self, session_id: str | None = None):
        def _callback(_):
            message_logged = False
            if session_id and session_id in self.sessions:
                session_info = self.sessions[session_id]
                logger.log(
                    self._log_level,
                    "🧹 Session %s garbage collected without explicit closure",
                    session_id,
                )
                message_logged = True
                if not session_info.is_closed:
                    session_info.is_closed = True

            if not message_logged:
                logger.log(self._log_level, "🧹 Garbage collected a session reference")

        return _callback

    def check_session_reference(self, session_id: str) -> None:
        if session_id and session_id in self.sessions:
            session_info = self.sessions[session_id]
            if session_info.is_closed:
                logger.log(
                    self._log_level,
                    "🧹 Session %s already closed by GC (closing mark)" % session_id,
                )

    def register_session_ref(self, session_id: str, session: SessionInfo) -> None:
        self.session_refs[session_id] = weakref.ref(session)
