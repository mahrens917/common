"""State cleanup helpers for backoff management."""

import logging
import time
from typing import Any, Dict, List

from .types import BackoffType

logger = logging.getLogger(__name__)


class StateCleaner:
    """Cleans up old backoff state entries."""

    @staticmethod
    def cleanup_old_state(backoff_state: Dict[str, Dict[BackoffType, Dict[str, Any]]], max_age_seconds: int = 3600) -> None:
        """
        Clean up old backoff state entries to prevent memory leaks.

        Args:
            backoff_state: The backoff state dictionary to clean
            max_age_seconds: Maximum age of backoff state to keep
        """
        current_time = time.time()
        services_to_remove: List[str] = []

        for service_name, service_state in backoff_state.items():
            types_to_remove: List[BackoffType] = []

            for backoff_type, state in service_state.items():
                if current_time - state["last_failure_time"] > max_age_seconds:
                    types_to_remove.append(backoff_type)

            for backoff_type in types_to_remove:
                del service_state[backoff_type]

            if not service_state:
                services_to_remove.append(service_name)

        for service_name in services_to_remove:
            del backoff_state[service_name]

        if services_to_remove:
            logger.debug(f"[BackoffManager] Cleaned up old backoff state: " f"removed {len(services_to_remove)} services")
