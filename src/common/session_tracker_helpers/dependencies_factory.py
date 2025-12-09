"""Dependency factory for SessionTracker."""

from dataclasses import dataclass
from typing import Dict

from .activity_tracker import SessionActivityTracker
from .cleanup import SessionCleanup
from .gc_handler import GarbageCollectionHandler
from .id_generator import SessionIdGenerator
from .lifecycle import SessionLifecycleTracker
from .reporter import SessionReporter
from .session_queries import SessionQueries


@dataclass
class SessionTrackerDependencies:
    """Dependencies for SessionTracker."""

    id_generator: SessionIdGenerator
    gc_handler: GarbageCollectionHandler
    lifecycle: SessionLifecycleTracker
    activity: SessionActivityTracker
    queries: SessionQueries
    reporter: SessionReporter
    cleanup: SessionCleanup


class SessionTrackerDependenciesFactory:
    """Factory for creating SessionTracker dependencies."""

    @staticmethod
    def create(sessions: Dict, session_refs: Dict, log_level: int) -> SessionTrackerDependencies:
        """
        Create all dependencies for SessionTracker.

        Args:
            sessions: Session tracking dictionary
            session_refs: Session reference dictionary
            log_level: Logging level for session tracking

        Returns:
            SessionTrackerDependencies instance
        """
        id_generator = SessionIdGenerator()
        gc_handler = GarbageCollectionHandler(sessions, session_refs, log_level)
        lifecycle = SessionLifecycleTracker(sessions, session_refs, log_level)
        activity = SessionActivityTracker(sessions, log_level)
        queries = SessionQueries(sessions, session_refs)
        reporter = SessionReporter(log_level)
        cleanup = SessionCleanup(sessions, session_refs, log_level)

        return SessionTrackerDependencies(
            id_generator=id_generator,
            gc_handler=gc_handler,
            lifecycle=lifecycle,
            activity=activity,
            queries=queries,
            reporter=reporter,
            cleanup=cleanup,
        )
