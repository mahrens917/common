"""
Session lifecycle tracking utility for diagnosing unclosed aiohttp.ClientSession instances.

This module provides centralized tracking of HTTP session creation, usage, and cleanup
to help identify sources of "Unclosed client session" warnings.
"""

import logging
import weakref
from typing import Dict, Optional

import aiohttp

from common.config import env_str
from common.session_tracker_helpers.dependencies_factory import (
    SessionTrackerDependencies,
    SessionTrackerDependenciesFactory,
)
from common.session_tracker_helpers.models import SessionInfo
from common.session_tracker_mixins import (
    SessionTrackerActivityMixin,
    SessionTrackerQueryMixin,
    SessionTrackerSyncMixin,
)

logger = logging.getLogger(__name__)

__all__ = [
    "SessionTracker",
    "session_tracker",
    "tracked_session",
    "track_existing_session",
    "track_session_request",
    "track_session_close",
    "log_session_diagnostics",
    "SESSION_TRACKING_LOG_LEVEL",
]

# Configurable logging level for session tracking
_SESSION_TRACKING_LOG_LEVEL_VALUE = env_str("SESSION_TRACKING_LOG_LEVEL") or "DEBUG"
if _SESSION_TRACKING_LOG_LEVEL_VALUE:
    _SESSION_TRACKING_LOG_LEVEL_NAME = _SESSION_TRACKING_LOG_LEVEL_VALUE.upper()
else:
    _SESSION_TRACKING_LOG_LEVEL_NAME = "DEBUG"
SESSION_TRACKING_LOG_LEVEL = getattr(logging, _SESSION_TRACKING_LOG_LEVEL_NAME, logging.DEBUG)


class SessionTracker(
    SessionTrackerSyncMixin,
    SessionTrackerActivityMixin,
    SessionTrackerQueryMixin,
):
    """
    Centralized tracker for aiohttp.ClientSession lifecycle management.

    Provides diagnostic logging and monitoring for session creation, usage,
    and cleanup to help identify sources of unclosed sessions.
    """

    _instance: Optional["SessionTracker"] = None

    def __new__(cls):
        """Singleton pattern to ensure only one tracker exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        if name in {"sessions", "session_refs"}:
            self._sync_dependency_references()

    def __init__(self, *, dependencies: Optional[SessionTrackerDependencies] = None):
        """Initialize session tracker."""
        if hasattr(self, "_initialized"):
            return

        self.sessions: Dict[str, SessionInfo] = {}
        self.session_refs: Dict[str, weakref.ReferenceType] = {}
        self._initialized = True
        logger.setLevel(SESSION_TRACKING_LOG_LEVEL)

        deps = dependencies or SessionTrackerDependenciesFactory.create(self.sessions, self.session_refs, SESSION_TRACKING_LOG_LEVEL)
        self._id_generator = deps.id_generator
        self._gc_handler = deps.gc_handler
        self._lifecycle = deps.lifecycle
        self._activity = deps.activity
        self._queries = deps.queries
        self._reporter = deps.reporter
        self._cleanup = deps.cleanup

        logger.log(SESSION_TRACKING_LOG_LEVEL, "🔍 Session tracker initialized")
        self._sync_dependency_references()

    def track_session_creation(self, session: aiohttp.ClientSession, service_name: str) -> str:
        """
        Track creation of a new HTTP session.

        Args:
            session: The aiohttp.ClientSession instance
            service_name: Name of the service creating the session

        Returns:
            Unique session ID for tracking
        """
        session_id = self._id_generator.generate()
        self._lifecycle.track_creation(session, session_id, service_name)
        self.session_refs[session_id] = weakref.ref(session, self._gc_handler.create_callback(session_id))
        return session_id


# Global session tracker instance
session_tracker = SessionTracker()


# Import context manager utilities
from contextlib import asynccontextmanager  # noqa: E402


@asynccontextmanager
async def tracked_session(service_name: str, **session_kwargs):
    """
    Context manager for creating and tracking an aiohttp.ClientSession.

    Args:
        service_name: Name of the service creating the session
        **session_kwargs: Arguments to pass to aiohttp.ClientSession

    Yields:
        Tuple of (session, session_id) for the tracked session
    """
    session = aiohttp.ClientSession(**session_kwargs)
    session_id = session_tracker.track_session_creation(session, service_name)

    try:
        yield session, session_id
    finally:
        session_tracker.track_session_closure(session_id)
        if not session.closed:
            await session.close()


def track_existing_session(session: aiohttp.ClientSession, service_name: str) -> str:
    """
    Track an existing aiohttp.ClientSession instance.

    Args:
        session: Existing session to track
        service_name: Name of the service that owns the session

    Returns:
        Session ID for tracking
    """
    return session_tracker.track_session_creation(session, service_name)


def track_session_request(session_id: str):
    """
    Track a request made with a tracked session.

    Args:
        session_id: Session ID returned from track_session_creation
    """
    session_tracker.track_session_activity(session_id)


def track_session_close(session_id: str):
    """
    Track explicit closure of a session.

    Args:
        session_id: Session ID returned from track_session_creation
    """
    session_tracker.track_session_closure(session_id)


async def log_session_diagnostics():
    """Log diagnostic information about all tracked sessions."""
    session_tracker.log_session_summary()
    session_tracker.cleanup_old_session_records()
