"""Handle subscription updates from Redis pub/sub."""

import logging
from typing import Callable, Dict, List, Tuple

from ...redis_protocol import SubscriptionUpdate

logger = logging.getLogger(__name__)


class UpdateHandler:
    """Handles subscription update processing."""

    def __init__(
        self,
        service_name: str,
        websocket_client,
        active_instruments: Dict[str, Dict],
        pending_subscriptions: List[Tuple[str, str, str]],
        api_type_mapper: Callable[[str], str],
    ):
        """
        Initialize update handler.

        Args:
            service_name: Name of the service
            websocket_client: WebSocket client instance
            active_instruments: Reference to active instruments dict
            pending_subscriptions: Reference to pending subscriptions list
            api_type_mapper: Function to map subscription type to API type
        """
        self.service_name = service_name
        self.websocket_client = websocket_client
        self.active_instruments = active_instruments
        self.pending_subscriptions = pending_subscriptions
        self._api_type_mapper = api_type_mapper

    async def handle_update(self, update: SubscriptionUpdate, redis_client) -> None:
        """
        Handle subscription update from Redis pub/sub.

        Args:
            update: Subscription update message
            redis_client: Redis client for operations
        """
        name = update.name
        action = update.action
        api_type = self._api_type_mapper(update.subscription_type)

        if action == "subscribe":
            await self._handle_subscribe(name, api_type)
        elif action == "unsubscribe":
            await self._handle_unsubscribe(name, api_type, redis_client)

    async def _handle_subscribe(self, name: str, api_type: str) -> None:
        """Handle subscription request."""
        if name not in self.active_instruments:
            tracking_key = name
            channel = name

            # Add to pending subscriptions
            self.pending_subscriptions.append((tracking_key, api_type, channel))
            logger.info(f"Queued {self.service_name} subscription for: {name}")

    async def _handle_unsubscribe(self, name: str, api_type: str, redis_client) -> None:
        """Handle unsubscription request."""
        if name in self.active_instruments:
            channel = name

            try:
                # Attempt to unsubscribe
                await self.websocket_client.unsubscribe([channel])

                # Remove from active instruments if unsubscribe succeeded
                if channel not in self.websocket_client.active_subscriptions:
                    self.active_instruments.pop(name, None)
                    logger.info(f"Unsubscribed from {self.service_name} channel: {name}")
                else:
                    logger.error(f"Failed to unsubscribe from {self.service_name} channel: {channel}")

            except (  # policy_guard: allow-silent-handler
                ConnectionError,
                RuntimeError,
                ValueError,
            ):
                logger.exception(
                    "Error unsubscribing from %s channel %s",
                    self.service_name,
                    channel,
                )
