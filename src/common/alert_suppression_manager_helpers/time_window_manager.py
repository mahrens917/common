"""Time window calculations for grace periods and suppression durations."""

import time
from dataclasses import dataclass
from typing import Optional

from ..connection_state_tracker import ConnectionStateTracker


@dataclass(frozen=True)
class TimeWindowContext:
    """Context information about time windows for suppression decisions."""

    is_in_reconnection: bool
    is_in_grace_period: bool
    reconnection_duration: Optional[float]
    grace_period_remaining_seconds: Optional[float]


class TimeWindowManager:
    """Manages time-based calculations for alert suppression."""

    async def build_time_context(
        self,
        service_name: str,
        grace_period_seconds: int,
        state_tracker: ConnectionStateTracker,
    ) -> TimeWindowContext:
        """
        Build time window context for suppression evaluation.

        Args:
            service_name: Name of the service
            grace_period_seconds: Grace period duration in seconds
            state_tracker: Connection state tracker instance

        Returns:
            TimeWindowContext with time-related information
        """
        is_in_reconnection = await state_tracker.is_service_in_reconnection(service_name)
        is_in_grace_period = await state_tracker.is_service_in_grace_period(
            service_name, grace_period_seconds
        )
        reconnection_duration = await state_tracker.get_reconnection_duration(service_name)

        grace_period_remaining = None
        if is_in_grace_period:
            connection_state = await state_tracker.get_connection_state(service_name)
            if connection_state and connection_state.last_successful_connection:
                elapsed = time.time() - connection_state.last_successful_connection
                grace_period_remaining = max(0.0, grace_period_seconds - elapsed)

        return TimeWindowContext(
            is_in_reconnection=is_in_reconnection,
            is_in_grace_period=is_in_grace_period,
            reconnection_duration=reconnection_duration,
            grace_period_remaining_seconds=grace_period_remaining,
        )
