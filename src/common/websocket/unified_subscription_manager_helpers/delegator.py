"""Delegator for UnifiedSubscriptionManager operations."""

from typing import Dict, List, Tuple

from .factory import UnifiedSubscriptionManagerFactory


class UnifiedSubscriptionManagerDelegator:
    """Delegates operations to specialized components."""

    def __init__(
        self,
        service_name: str,
        websocket_client,
        subscription_channel: str,
        active_instruments: Dict[str, Dict],
        pending_subscriptions: List[Tuple[str, str, str]],
        api_type_mapper,
    ):
        """
        Initialize delegator with components.

        Args:
            service_name: Name of the service
            websocket_client: WebSocket client instance
            subscription_channel: Redis channel for subscription updates
            active_instruments: Reference to active instruments dict
            pending_subscriptions: Reference to pending subscriptions list
            api_type_mapper: Function to map subscription type to API type
        """
        # Create components via factory
        self.lifecycle_manager, self.monitoring_loop = (
            UnifiedSubscriptionManagerFactory.create_components(
                service_name,
                websocket_client,
                subscription_channel,
                active_instruments,
                pending_subscriptions,
                api_type_mapper,
            )
        )

    async def start_monitoring(self) -> None:
        """Start Redis pub/sub monitoring."""
        await self.lifecycle_manager.start_monitoring(self.monitoring_loop.run())

    async def stop_monitoring(self) -> None:
        """Stop subscription monitoring."""
        await self.lifecycle_manager.stop_monitoring()
