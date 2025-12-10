"""Mixin classes for SessionTracker functionality."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    import weakref

    from common.session_tracker_helpers.models import SessionInfo


class SessionTrackerSyncMixin:
    """Mixin for dependency reference synchronization."""

    sessions: Dict[str, SessionInfo]
    session_refs: Dict[str, weakref.ReferenceType]
    _lifecycle: Any
    _activity: Any
    _cleanup: Any
    _queries: Any
    _gc_handler: Any

    def _sync_dependency_references(self) -> None:
        """Keep dependency references aligned with the mutable session dictionaries."""
        if not hasattr(self, "_lifecycle"):
            return
        sessions = getattr(self, "sessions", None)
        session_refs = getattr(self, "session_refs", None)
        if sessions is None or session_refs is None:
            return
        self._lifecycle.sessions = sessions
        self._lifecycle.session_refs = session_refs
        self._activity.sessions = sessions
        self._cleanup.sessions = sessions
        self._cleanup.session_refs = session_refs
        self._queries.sessions = sessions
        self._queries.session_refs = session_refs
        self._gc_handler.sessions = sessions
        self._gc_handler.session_refs = session_refs


class SessionTrackerActivityMixin:
    """Mixin for session activity tracking."""

    _activity: Any
    _lifecycle: Any

    def track_session_activity(self, session_id: str) -> None:
        """Track activity on a session (e.g., HTTP request made)."""
        self._activity.track_activity(session_id)

    def track_session_closure(self, session_id: str) -> None:
        """Track explicit closure of a session."""
        self._lifecycle.track_closure(session_id)


class SessionTrackerQueryMixin:
    """Mixin for session queries and reporting."""

    _queries: Any
    _reporter: Any
    _cleanup: Any

    def get_active_sessions(self) -> List[SessionInfo]:
        """Get list of currently active (unclosed) sessions."""
        return self._queries.get_active_sessions()

    def log_session_summary(self) -> None:
        """Log summary of all tracked sessions."""
        active_sessions = self.get_active_sessions()
        total_sessions = self._queries.get_total_session_count()
        self._reporter.log_summary(active_sessions, total_sessions)

    def cleanup_old_session_records(self, max_age_seconds: float = 3600) -> None:
        """Clean up tracking records for old closed sessions."""
        self._cleanup.cleanup_old_records(max_age_seconds)


__all__ = [
    "SessionTrackerSyncMixin",
    "SessionTrackerActivityMixin",
    "SessionTrackerQueryMixin",
]
