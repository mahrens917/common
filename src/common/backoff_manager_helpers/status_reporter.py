"""Status reporting helpers for backoff information."""

from typing import Any, Dict

from .state_manager import BackoffStateManager
from .types import BackoffConfig, BackoffType


class BackoffStatusReporter:
    """Reports backoff status information."""

    @staticmethod
    def get_backoff_info(
        state_manager: BackoffStateManager,
        service_name: str,
        backoff_type: BackoffType,
        config: BackoffConfig,
        next_delay: float,
    ) -> Dict[str, Any]:
        """
        Get current backoff information for a service and failure type.

        Args:
            state_manager: State manager instance
            service_name: Name of the service
            backoff_type: Type of failure
            config: Backoff configuration
            next_delay: Calculated next delay

        Returns:
            Dictionary with backoff state information
        """
        info = state_manager.get_backoff_info(service_name, backoff_type, config)
        info["next_delay"] = next_delay
        return info

    @staticmethod
    def get_all_backoff_status(
        state_manager: BackoffStateManager,
        configs: Dict[BackoffType, BackoffConfig],
        delay_calculator,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get backoff status for all services and failure types.

        Args:
            state_manager: State manager instance
            configs: Backoff configurations
            delay_calculator: Callable to calculate next delay

        Returns:
            Nested dictionary with all backoff state information
        """
        status = {}

        for service_name, service_state in state_manager.backoff_state.items():
            status[service_name] = {}
            for backoff_type, state in service_state.items():
                config = configs.get(backoff_type, configs[BackoffType.GENERAL_FAILURE])
                info = state_manager.get_backoff_info(service_name, backoff_type, config)

                # Calculate next delay
                next_delay = delay_calculator(service_name, backoff_type, state["attempt"] + 1)
                info["next_delay"] = next_delay

                status[service_name][backoff_type.value] = info

        return status
