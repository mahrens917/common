"""Factory for creating UnifiedSubscriptionManager components."""

from typing import Callable, Dict, List, Tuple

from .health_validator import HealthValidator
from .lifecycle_manager import LifecycleManager
from .monitoring_loop import MonitoringLoop
from .subscription_processor import SubscriptionProcessor
from .update_handler import UpdateHandler


class UnifiedSubscriptionManagerFactory:
    """Factory for creating subscription manager components."""

    @staticmethod
    def create_components(
        service_name: str,
        websocket_client,
        subscription_channel: str,
        active_instruments: Dict[str, Dict],
        pending_subscriptions: List[Tuple[str, str, str]],
        api_type_mapper: Callable[[str], str],
    ) -> tuple:
        """
        Create all components for subscription management.

        Args:
            service_name: Name of the service
            websocket_client: WebSocket client instance
            subscription_channel: Redis channel for subscription updates
            active_instruments: Reference to active instruments dict
            pending_subscriptions: Reference to pending subscriptions list
            api_type_mapper: Function to map subscription type to API type

        Returns:
            Tuple of (lifecycle_manager, monitoring_loop)
        """
        # Create lifecycle manager
        lifecycle_manager = LifecycleManager(service_name)

        # Create update handler
        update_handler = UpdateHandler(
            service_name,
            websocket_client,
            active_instruments,
            pending_subscriptions,
            api_type_mapper,
        )

        # Create subscription processor
        subscription_processor = SubscriptionProcessor(
            service_name,
            websocket_client,
            active_instruments,
            pending_subscriptions,
        )

        # Create health validator
        health_validator = HealthValidator(
            service_name,
            websocket_client,
            active_instruments,
        )

        # Create monitoring loop
        monitoring_loop = MonitoringLoop(
            service_name,
            subscription_channel,
            update_handler,
            subscription_processor,
            health_validator,
        )

        return lifecycle_manager, monitoring_loop
