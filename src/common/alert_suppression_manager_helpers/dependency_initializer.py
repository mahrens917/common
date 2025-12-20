"""Dependency initialization for alert suppression manager."""

from __future__ import annotations

import logging
from typing import Optional

from ..connection_state_tracker import ConnectionStateTracker, get_connection_state_tracker
from ..reconnection_error_patterns import ReconnectionErrorClassifier, get_error_classifier

logger = logging.getLogger(__name__)


class DependencyInitializer:
    """Manages initialization of external dependencies."""

    def __init__(self):
        """Initialize dependency initializer."""
        self.state_tracker: Optional[ConnectionStateTracker] = None
        self.error_classifier: Optional[ReconnectionErrorClassifier] = None

    async def initialize(self) -> None:
        """Initialize dependencies if not already initialized."""
        if self.state_tracker is None:
            self.state_tracker = await get_connection_state_tracker()

        if self.error_classifier is None:
            self.error_classifier = get_error_classifier()

        logger.debug("Alert suppression manager dependencies initialized")

    def require_dependencies(self) -> tuple[ConnectionStateTracker, ReconnectionErrorClassifier]:
        """
        Ensure dependencies are initialized and return them.

        Returns:
            Tuple of (state_tracker, error_classifier)

        Raises:
            RuntimeError: If dependencies are not initialized
        """
        if self.state_tracker is None:
            raise RuntimeError("Alert suppression manager state tracker is not initialized")
        if self.error_classifier is None:
            raise RuntimeError("Alert suppression manager error classifier is not initialized")
        return self.state_tracker, self.error_classifier
