"""
Unified subscription manager for WebSocket services.

Provides common Redis pub/sub subscription management for both Deribit and Kalshi
WebSocket services. Implements fail-fast error handling and subscription health validation.
"""

import logging
from typing import Dict, List, Tuple

from ..redis_protocol.messages import SubscriptionUpdate
from .interfaces import SubscriptionAwareWebSocketClient
from .unified_subscription_manager_helpers import UnifiedSubscriptionManagerDelegator

logger = logging.getLogger(__name__)

__all__ = [
    "UnifiedSubscriptionManager",
    "SubscriptionHealthError",
    "SubscriptionUpdate",
]


class SubscriptionHealthError(Exception):
    """Raised when subscription health validation fails."""

    pass


class UnifiedSubscriptionManager:
    """
    Unified subscription manager with fail-fast health validation.

    Manages Redis pub/sub subscriptions for WebSocket services and validates
    subscription health to prevent zombie connection states.
    """

    def __init__(
        self,
        service_name: str,
        websocket_client: SubscriptionAwareWebSocketClient,
        subscription_channel: str,
        subscription_key: str,
    ):
        """
        Initialize unified subscription manager.

        Args:
            service_name: Name of the service (e.g., 'deribit', 'kalshi')
            websocket_client: WebSocket client instance
            subscription_channel: Redis channel for subscription updates
            subscription_key: Redis key for subscription storage
        """
        self.service_name = service_name
        self.websocket_client = websocket_client
        self.subscription_channel = subscription_channel
        self.subscription_key = subscription_key
        self.active_instruments: Dict[str, Dict] = {}
        self.pending_subscriptions: List[Tuple[str, str, str]] = (
            []
        )  # [(tracking_key, api_type, channel)]
        self.waiting_for_subscriptions = False
        self._last_health_check = 0.0

        # Create delegator for all operations
        self._delegator = UnifiedSubscriptionManagerDelegator(
            service_name,
            websocket_client,
            subscription_channel,
            self.active_instruments,
            self.pending_subscriptions,
            self._get_api_type,
        )

    async def start_monitoring(self) -> None:
        """Start Redis pub/sub monitoring."""
        await self._delegator.start_monitoring()

    async def stop_monitoring(self) -> None:
        """Stop subscription monitoring."""
        await self._delegator.stop_monitoring()

    def _get_api_type(self, subscription_type: str) -> str:
        """
        Map subscription type to API type.
        Override in service-specific implementations.
        """
        return subscription_type
