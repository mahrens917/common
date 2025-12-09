"""Retry checking helpers for backoff management."""

import logging

from .state_manager import BackoffStateManager
from .types import BackoffConfig, BackoffType

logger = logging.getLogger(__name__)


class RetryChecker:
    """Checks whether retries should be attempted."""

    @staticmethod
    def should_retry(
        state_manager: BackoffStateManager,
        service_name: str,
        backoff_type: BackoffType,
        config: BackoffConfig,
    ) -> bool:
        """
        Check if a retry should be attempted based on max attempts configuration.

        Args:
            state_manager: State manager instance
            service_name: Name of the service
            backoff_type: Type of failure
            config: Backoff configuration

        Returns:
            True if retry should be attempted, False if max attempts reached
        """
        info = state_manager.get_backoff_info(service_name, backoff_type, config)

        should_retry = info["can_retry"]
        if not should_retry:
            logger.warning(
                f"[BackoffManager] Max attempts ({config.max_attempts}) reached for {service_name}/{backoff_type.value}"
            )

        return should_retry
