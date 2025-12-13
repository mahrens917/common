"""Notification handling for dependency status changes."""

import logging
from functools import partial
from typing import Callable, Optional

from common.truthy import pick_if

from .dependency_checker import DependencyStatus

logger = logging.getLogger(__name__)


class NotificationHandler:
    """Handles notifications about dependency status changes."""

    @staticmethod
    async def notify_status_change(
        dependency_name: str,
        old_status: DependencyStatus,
        new_status: DependencyStatus,
        service_name: str,
        redis_tracker,
        telegram_notifier: Optional[Callable],
        callback_executor,
    ) -> None:
        """Notify about dependency status changes."""
        if redis_tracker:
            await redis_tracker.update_dependency_status(dependency_name, new_status)

        if old_status == DependencyStatus.UNKNOWN:
            return

        status_emoji = pick_if(new_status == DependencyStatus.AVAILABLE, lambda: "✅", lambda: "❌")
        message = f"{status_emoji} [{service_name}] Dependency '{dependency_name}': {old_status.value} → {new_status.value}"

        logger.info(message)

        if telegram_notifier:
            error = await callback_executor.run_callback(partial(telegram_notifier, message))
            if isinstance(error, BaseException):
                logger.error("[%s] Failed to send Telegram notification: %s", service_name, error)
