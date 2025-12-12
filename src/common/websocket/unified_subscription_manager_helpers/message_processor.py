"""Process messages from Redis pub/sub."""

import logging

from ...redis_protocol import SubscriptionUpdate
from ...redis_protocol.error_types import PARSING_ERRORS

logger = logging.getLogger(__name__)

UPDATE_PARSE_ERRORS = PARSING_ERRORS + (KeyError, ValueError)


class MessageProcessor:
    """Processes messages from Redis pub/sub."""

    def __init__(
        self,
        service_name: str,
        update_handler,
        subscription_processor,
        health_validator,
    ):
        """
        Initialize message processor.

        Args:
            service_name: Name of the service
            update_handler: Handler for subscription updates
            subscription_processor: Processor for pending subscriptions
            health_validator: Validator for subscription health
        """
        self.service_name = service_name
        self.update_handler = update_handler
        self.subscription_processor = subscription_processor
        self.health_validator = health_validator

    async def process_message(self, message, redis_client) -> None:
        """
        Process a single message.

        Args:
            message: Message from Redis pub/sub
            redis_client: Redis client for operations
        """
        if not isinstance(message, dict) or message.get("type") != "message":
            return

        data = message.get("data")
        if not data or not isinstance(data, str):
            return

        update = self._parse_update(data)
        if update is None:
            return

        # Process subscription update
        await self.update_handler.handle_update(update, redis_client)

        # Process pending subscriptions
        await self.subscription_processor.process_pending()

        # Validate subscription health
        await self.health_validator.validate_health()

    def _parse_update(self, data: str) -> SubscriptionUpdate | None:
        """Parse subscription update from data."""
        try:
            return SubscriptionUpdate.from_json(data)
        except UPDATE_PARSE_ERRORS as exc:  # policy_guard: allow-silent-handler
            logger.exception("Failed to parse %s subscription update: %s", self.service_name, data, exc_info=exc)
            return None
