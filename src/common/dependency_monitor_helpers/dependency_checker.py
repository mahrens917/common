"""Dependency checking logic for dependency monitor."""

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

logger = logging.getLogger(__name__)


DEFAULT_DEPENDENCY_MAX_CHECK_INTERVAL_SECONDS = 300.0


class DependencyStatus(Enum):
    """Dependency status values"""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


@dataclass
class DependencyConfig:
    """Configuration for a single dependency"""

    name: str
    check_function: Callable[[], object]
    check_interval_seconds: float = 30.0
    max_check_interval_seconds: float = DEFAULT_DEPENDENCY_MAX_CHECK_INTERVAL_SECONDS
    backoff_multiplier: float = 1.5
    required: bool = True


@dataclass
class DependencyState:
    """Current state of a dependency"""

    config: DependencyConfig
    status: DependencyStatus = DependencyStatus.UNKNOWN
    last_check_time: float = 0.0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    current_check_interval: float = 0.0
    last_status_change_time: float = 0.0


class DependencyChecker:
    """Performs dependency checks and updates state."""

    def __init__(self, service_name: str, callback_executor):
        """
        Initialize dependency checker.

        Args:
            service_name: Name of service
            callback_executor: Callback executor instance
        """
        self.service_name = service_name
        self.callback_executor = callback_executor

    async def check_dependency(
        self, state: DependencyState, notifier_callback: Optional[Callable] = None
    ) -> DependencyStatus:
        """
        Check a single dependency.

        Args:
            state: Dependency state to check
            notifier_callback: Callback to notify status changes

        Returns:
            New dependency status
        """
        current_time = time.time()
        state.last_check_time = current_time

        result, error = await self.callback_executor.invoke_check_function(
            state.config.check_function
        )

        if isinstance(error, BaseException):
            logger.error(
                "[%s] Error checking dependency %s: %s",
                self.service_name,
                state.config.name,
                error,
            )
            return await self._handle_check_error(state, current_time, notifier_callback)

        is_available = bool(result)
        new_status = DependencyStatus.AVAILABLE if is_available else DependencyStatus.UNAVAILABLE

        return await self._update_state(state, new_status, current_time, notifier_callback)

    async def _handle_check_error(
        self, state: DependencyState, current_time: float, notifier_callback: Optional[Callable]
    ) -> DependencyStatus:
        """Handle check function error."""
        if state.status != DependencyStatus.UNAVAILABLE:
            old_status = state.status
            state.status = DependencyStatus.UNAVAILABLE
            state.last_status_change_time = current_time
            if notifier_callback:
                await notifier_callback(state.config.name, old_status, DependencyStatus.UNAVAILABLE)

        state.consecutive_failures += 1
        state.consecutive_successes = 0

        state.current_check_interval = min(
            state.current_check_interval * state.config.backoff_multiplier,
            state.config.max_check_interval_seconds,
        )

        return DependencyStatus.UNAVAILABLE

    async def _update_state(
        self,
        state: DependencyState,
        new_status: DependencyStatus,
        current_time: float,
        notifier_callback: Optional[Callable],
    ) -> DependencyStatus:
        """Update dependency state based on check result."""
        if new_status == DependencyStatus.AVAILABLE:
            state.consecutive_failures = 0
            state.consecutive_successes += 1
            state.current_check_interval = state.config.check_interval_seconds
        else:
            state.consecutive_successes = 0
            state.consecutive_failures += 1
            state.current_check_interval = min(
                state.current_check_interval * state.config.backoff_multiplier,
                state.config.max_check_interval_seconds,
            )

        if state.status != new_status:
            old_status = state.status
            state.status = new_status
            state.last_status_change_time = current_time

            if notifier_callback:
                await notifier_callback(state.config.name, old_status, new_status)

        return new_status
