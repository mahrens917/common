"""Status change management for dependency monitor."""

import asyncio
import logging
from functools import partial
from typing import Callable, Dict, List, Optional

from .dependency_checker import DependencyState, DependencyStatus

logger = logging.getLogger(__name__)


class StatusManager:
    """Manages overall service status based on dependency states."""

    def __init__(
        self,
        service_name: str,
        dependencies: Dict[str, DependencyState],
        callback_executor,
        telegram_notifier: Optional[Callable] = None,
        redis_tracker=None,
    ):
        """
        Initialize status manager.

        Args:
            service_name: Name of service
            dependencies: Dictionary of dependency states
            callback_executor: Callback executor instance
            telegram_notifier: Optional Telegram notifier
            redis_tracker: Optional Redis tracker
        """
        self.service_name = service_name
        self.dependencies = dependencies
        self.callback_executor = callback_executor
        self.telegram_notifier = telegram_notifier
        self.redis_tracker = redis_tracker
        self._recovery_callbacks: List[Callable] = []
        self._failure_callbacks: List[Callable] = []
        self._has_been_available = False
        self._is_currently_available = False

    def add_recovery_callback(self, callback: Callable) -> None:
        """Add recovery callback."""
        self._recovery_callbacks.append(callback)

    def add_failure_callback(self, callback: Callable) -> None:
        """Add failure callback."""
        self._failure_callbacks.append(callback)

    def are_required_dependencies_available(self) -> bool:
        """Check if all required dependencies are available."""
        for state in self.dependencies.values():
            if state.config.required and state.status != DependencyStatus.AVAILABLE:
                return False
        return True

    async def handle_status_changes(self) -> None:
        """Handle overall service status changes based on dependency status."""
        required_available = self.are_required_dependencies_available()

        was_available = self._is_currently_available
        self._is_currently_available = required_available

        if required_available and not was_available:
            if self._has_been_available:
                logger.info(
                    f"[{self.service_name}] Dependencies recovered, triggering recovery callbacks"
                )
                await self._run_callbacks(self._recovery_callbacks)
            else:
                logger.info(f"[{self.service_name}] All required dependencies available on startup")
                self._has_been_available = True
        elif not required_available and was_available:
            logger.warning(
                f"[{self.service_name}] Required dependencies failed, triggering failure callbacks"
            )
            await self._run_callbacks(self._failure_callbacks)

    async def _run_callbacks(self, callbacks: List[Callable]) -> None:
        """Run list of callbacks."""
        for callback in callbacks:
            try:
                error = await self.callback_executor.run_callback(callback)
            except asyncio.CancelledError:
                raise
            except (RuntimeError, ValueError, TypeError, AttributeError, Exception):
                logger.exception("[%s] Error in callback", self.service_name)
                continue
            if isinstance(error, BaseException):
                logger.error("[%s] Error in callback: %s", self.service_name, error)

    async def notify_status_change(
        self, dependency_name: str, old_status: DependencyStatus, new_status: DependencyStatus
    ) -> None:
        """Notify about dependency status changes."""
        if self.redis_tracker:
            await self.redis_tracker.update_dependency_status(dependency_name, new_status)

        if old_status == DependencyStatus.UNKNOWN:
            return

        status_emoji = "✅" if new_status == DependencyStatus.AVAILABLE else "❌"
        message = f"{status_emoji} [{self.service_name}] Dependency '{dependency_name}': {old_status.value} → {new_status.value}"

        logger.info(message)

        if self.telegram_notifier:
            error = await self.callback_executor.run_callback(
                partial(self.telegram_notifier, message)
            )
            if isinstance(error, BaseException):
                logger.error(
                    "[%s] Failed to send Telegram notification: %s", self.service_name, error
                )
