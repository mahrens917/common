"""Process pending subscriptions."""

import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class SubscriptionProcessor:
    """Processes pending subscriptions."""

    def __init__(
        self,
        service_name: str,
        websocket_client,
        active_instruments: Dict[str, Dict],
        pending_subscriptions: List[Tuple[str, str, str]],
    ):
        """
        Initialize subscription processor.

        Args:
            service_name: Name of the service
            websocket_client: WebSocket client instance
            active_instruments: Reference to active instruments dict
            pending_subscriptions: Reference to pending subscriptions list
        """
        self.service_name = service_name
        self.websocket_client = websocket_client
        self.active_instruments = active_instruments
        self.pending_subscriptions = pending_subscriptions
        self.waiting_for_subscriptions = False

    async def process_pending(self) -> None:
        """Process any pending subscriptions."""
        if not self.pending_subscriptions or not self.websocket_client.is_connected:
            return

        if self.waiting_for_subscriptions:
            return  # Already processing

        self.waiting_for_subscriptions = True

        try:
            # Collect all channels and their metadata
            channels_to_subscribe = []
            subscription_metadata = {}  # Map channels to their tracking info

            for tracking_key, api_type, channel in self.pending_subscriptions:
                channels_to_subscribe.append(channel)
                subscription_metadata[channel] = (tracking_key, api_type)

            if channels_to_subscribe:
                logger.info(
                    f"Processing {len(channels_to_subscribe)} pending {self.service_name} subscriptions"
                )

                # Subscribe to all channels
                success = await self.websocket_client.subscribe(channels_to_subscribe)

                if success:
                    # Update active instruments for successful subscriptions
                    for channel, (tracking_key, api_type) in subscription_metadata.items():
                        self.active_instruments[tracking_key] = {"api_type": api_type}
                    logger.info(
                        f"Successfully subscribed to {len(channels_to_subscribe)} {self.service_name} channels"
                    )
                else:
                    logger.error(f"Failed to process pending {self.service_name} subscriptions")

            # Clear pending subscriptions
            self.pending_subscriptions.clear()

        except (
            ConnectionError,
            RuntimeError,
            ValueError,
        ):
            logger.exception("Error processing pending %s subscriptions", self.service_name)
        finally:
            self.waiting_for_subscriptions = False
