"""Context building for alert suppression evaluation."""

from typing import Optional

from ..connection_state_tracker import ConnectionStateTracker
from ..reconnection_error_patterns import ReconnectionErrorClassifier
from .alert_evaluator import SuppressionContext
from .time_window_manager import TimeWindowManager


class ContextBuilder:
    """Builds suppression context from state tracker and error classifier."""

    def __init__(self, time_window_manager: TimeWindowManager):
        """
        Initialize context builder.

        Args:
            time_window_manager: Time window manager instance
        """
        self.time_window_manager = time_window_manager

    async def build_context(
        self,
        *,
        service_name: str,
        service_type: str,
        grace_period_seconds: int,
        error_message: Optional[str],
        state_tracker: ConnectionStateTracker,
        error_classifier: ReconnectionErrorClassifier,
        require_reconnection_error_pattern: bool,
    ) -> SuppressionContext:
        """
        Build complete suppression context.

        Args:
            service_name: Name of the service
            service_type: Type of service (websocket, rest, etc)
            grace_period_seconds: Grace period duration
            error_message: Optional error message
            state_tracker: Connection state tracker instance
            error_classifier: Error classifier instance
            require_reconnection_error_pattern: Whether to require error pattern matching

        Returns:
            SuppressionContext with all evaluation data
        """
        time_context = await self.time_window_manager.build_time_context(
            service_name=service_name,
            grace_period_seconds=grace_period_seconds,
            state_tracker=state_tracker,
        )

        is_reconnection_error = self._determine_reconnection_error(
            error_classifier=error_classifier,
            service_type=service_type,
            error_message=error_message,
            require_pattern=require_reconnection_error_pattern,
        )

        return SuppressionContext(
            service_type=service_type,
            is_in_reconnection=time_context.is_in_reconnection,
            is_in_grace_period=time_context.is_in_grace_period,
            reconnection_duration=time_context.reconnection_duration,
            grace_period_remaining_seconds=time_context.grace_period_remaining_seconds,
            is_reconnection_error=is_reconnection_error,
        )

    def _determine_reconnection_error(
        self,
        *,
        error_classifier: ReconnectionErrorClassifier,
        service_type: str,
        error_message: Optional[str],
        require_pattern: bool,
    ) -> bool:
        """Determine if error matches reconnection pattern."""
        if not require_pattern:
            return True
        if not error_message:
            return False
        return error_classifier.is_reconnection_error_by_type(service_type, error_message)
